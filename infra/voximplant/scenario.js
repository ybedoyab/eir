/**
 * EIR recovery check-in. Two entry points, one conversation.
 *
 *   AppEvents.Started       EIR places the call   (PSTN, or a registered user)
 *   AppEvents.CallAlerting  the patient's browser dials in over WebRTC
 *
 * Both converge on driveCall(), so Gemini Live, the required
 * submit_recovery_checkin tool call, and the EIR callback are identical
 * regardless of how the audio leg was established.
 *
 * Custom data (max 200 bytes): {"eid","cid","n"[, "t":"user","u":"eir-preview-user"]}
 * Inbound legs are forced to the webrtc transport by the entry point itself --
 * never by custom data, which the browser controls.
 * PSTN destination and Caller ID come from VoxEngine secret storage only.
 * Do not log phones, tokens, passwords, or transcripts.
 */
require(Modules.Gemini);

var GEMINI_LIVE_MODEL = 'gemini-live-2.5-flash-native-audio';
var GEMINI_LIVE_VOICE = 'Sulafat';
var VERTEX_PROJECT = 'eir-ata';
var VERTEX_LOCATION = 'us-central1';
var PREVIEW_USERNAME = 'eir-preview-user';
var NO_ANSWER_CODES = {408: true, 480: true, 487: true};
var TIMEOUT_MS_DIALLED = 90000;
var TIMEOUT_MS_WEBRTC = 180000;

var SYSTEM_PROMPT =
  'You are EIR, an automated recovery assistant calling after a recent visit. ' +
  'Speak calmly, warmly, and concisely. Do not sound overly enthusiastic. ' +
  'Take natural turns. Ask one question at a time. Briefly acknowledge answers. ' +
  'You are not a human clinician. Do not diagnose, name a suspected disease or ' +
  'complication, prescribe, change medication, or give unsupported medical conclusions. ' +
  'If concerning information appears, say you will flag it for the care team rather ' +
  'than assume what it means. Collect: pain score 0-10, whether symptoms are new or ' +
  'worsening, swelling or another reported issue, medication adherence (yes/no/unknown), ' +
  'whether the patient wants clinician follow-up, and a short neutral summary. ' +
  'Aim for a 30-60 second check-in. When you have enough information, call ' +
  'submit_recovery_checkin. Then give a brief closing statement.';

var TOOLS = [
  {
    functionDeclarations: [
      {
        name: 'submit_recovery_checkin',
        description: 'Submit the structured recovery check-in. Do not diagnose.',
        parametersJsonSchema: {
          type: 'object',
          properties: {
            pain_score: {type: 'integer', description: 'Pain score from 0 to 10'},
            reported_issue: {type: 'boolean'},
            issue_summary: {
              type: 'string',
              description: 'Short neutral summary of any reported issue',
            },
            symptoms_worsening: {type: 'boolean'},
            medication_adherence: {type: 'string', enum: ['yes', 'no', 'unknown']},
            patient_requests_clinician: {type: 'boolean'},
            call_outcome: {type: 'string', enum: ['completed']},
          },
          required: [
            'pain_score',
            'reported_issue',
            'issue_summary',
            'symptoms_worsening',
            'medication_adherence',
            'patient_requests_clinician',
            'call_outcome',
          ],
        },
      },
    ],
  },
];

function secret(name) {
  var value = VoxEngine.getSecretValue(name);
  if (typeof value === 'undefined' || value === null || value === '') {
    throw new Error('missing_secret');
  }
  return value;
}

function previewUsername(raw) {
  var user = String(raw || PREVIEW_USERNAME);
  if (!user || user.charAt(0) === '+' || user.indexOf('@') !== -1 || /^\d+$/.test(user)) {
    return PREVIEW_USERNAME;
  }
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]{1,49}$/.test(user)) {
    return PREVIEW_USERNAME;
  }
  return user.slice(0, 40);
}

function parseCustomData(raw, forcedTransport) {
  var data = JSON.parse(raw || '{}');
  if (!data.eid || !data.cid) {
    throw new Error('invalid_custom_data');
  }
  // forcedTransport wins: an inbound leg is WebRTC because of how it arrived,
  // not because the caller said so.
  var transport =
    forcedTransport ||
    (data.t === 'user' || data.transport === 'voximplant_user' ? 'voximplant_user' : 'pstn');
  return {
    episodeId: String(data.eid),
    correlationId: String(data.cid),
    displayName: String(data.n || 'Alex').slice(0, 24),
    transport: transport,
    destinationUser: previewUsername(data.u || PREVIEW_USERNAME),
    // Set only by encode_script_custom_data(outbound=True), i.e. a real
    // StartScenarios launch. A browser leg omits it.
    outbound: data.o === 1,
  };
}

function startDestinationCall(session) {
  if (session.transport === 'voximplant_user') {
    return VoxEngine.callUser({
      username: session.destinationUser,
      callerid: PREVIEW_USERNAME,
      displayName: 'EIR Recovery',
      video: false,
    });
  }
  return VoxEngine.callPSTN(session.destination, session.callerId);
}

function greetingText(session) {
  return (
    'Hi ' +
    session.displayName +
    ', this is EIR, the automated recovery assistant following up after your recent visit. ' +
    'Is now a good time for a quick recovery check-in?'
  );
}

function notify(session, state, extra) {
  extra = extra || {};
  var payload = {
    episode_id: session.episodeId,
    correlation_id: session.correlationId,
    state: state,
    call_id: session.callId || '',
    provider: 'voximplant',
  };
  for (var key in extra) {
    if (Object.prototype.hasOwnProperty.call(extra, key)) {
      payload[key] = extra[key];
    }
  }
  return Net.httpRequestAsync(session.callbackUrl, {
    method: 'POST',
    headers: [
      'Content-Type: application/json',
      'X-EIR-Voice-Token: ' + session.callbackToken,
    ],
    postData: JSON.stringify(payload),
    timeout: 8,
  }).catch(function () {
    return null;
  });
}

function clampPain(value) {
  var score = parseInt(value, 10);
  if (isNaN(score)) {
    return null;
  }
  if (score < 0) {
    return 0;
  }
  if (score > 10) {
    return 10;
  }
  return score;
}

function validateCheckin(args) {
  args = args || {};
  var pain = clampPain(args.pain_score);
  if (pain === null) {
    return null;
  }
  var adherence = args.medication_adherence;
  if (adherence !== 'yes' && adherence !== 'no') {
    adherence = 'unknown';
  }
  return {
    pain_score: pain,
    reported_issue: Boolean(args.reported_issue),
    issue_summary: String(args.issue_summary || '').slice(0, 240),
    symptoms_worsening: Boolean(args.symptoms_worsening),
    medication_adherence: adherence,
    patient_requests_clinician: Boolean(args.patient_requests_clinician),
    call_outcome: 'completed',
  };
}

function startGeminiLive(session, call, onSubmitted) {
  var credentials = secret('EIR_GEMINI_VERTEX_CREDENTIALS');
  return Gemini.createLiveAPIClient({
    credentials: credentials,
    model: GEMINI_LIVE_MODEL,
    backend: Gemini.Backend.VERTEX_AI,
    project: VERTEX_PROJECT,
    location: VERTEX_LOCATION,
    privacy: true,
    trace: false,
    connectConfig: {
      responseModalities: ['AUDIO'],
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: {voiceName: GEMINI_LIVE_VOICE},
        },
      },
      systemInstruction: {parts: [{text: SYSTEM_PROMPT}]},
      tools: TOOLS,
      inputAudioTranscription: {},
      outputAudioTranscription: {},
    },
    onWebSocketClose: function () {
      if (!onSubmitted()) {
        notify(session, 'CALL_FAILED', {failure_reason: 'gemini_closed'}).then(function () {
          VoxEngine.terminate();
        });
      }
    },
  }).then(function (voiceAIClient) {
    var started = false;

    function bindCallAudio() {
      VoxEngine.sendMediaBetween(call, voiceAIClient);
      try {
        if (voiceAIClient.sendMediaTo) {
          voiceAIClient.sendMediaTo(call);
        }
      } catch (error) {
        // ignore
      }
      try {
        if (call.sendMediaTo) {
          call.sendMediaTo(voiceAIClient);
        }
      } catch (error) {
        // ignore
      }
    }

    function startConversation() {
      if (started) {
        return;
      }
      started = true;
      bindCallAudio();
      voiceAIClient.sendRealtimeInput({
        text:
          'Begin now. Say exactly this greeting, then stop and wait for the patient: ' +
          greetingText(session),
      });
    }

    voiceAIClient.addEventListener(Gemini.LiveAPIEvents.SetupComplete, startConversation);
    if (Gemini.Events && Gemini.Events.WebSocketMediaStarted) {
      voiceAIClient.addEventListener(Gemini.Events.WebSocketMediaStarted, bindCallAudio);
    }

    function mergeUtterance(previous, next) {
      var a = String(previous || '').replace(/\s+/g, ' ').trim();
      var b = String(next || '').replace(/\s+/g, ' ').trim();
      if (!a) {
        return b;
      }
      if (!b) {
        return a;
      }
      if (b === a || b.indexOf(a) === 0 || (b.indexOf(a) !== -1 && b.length > a.length)) {
        return b;
      }
      if (a.indexOf(b) === 0 || a.indexOf(b) !== -1) {
        return a;
      }
      return a.length >= b.length ? a : b;
    }

    function pushTranscript(role, text, finished) {
      var clean = String(text || '')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 800);
      if (!clean) {
        return;
      }
      session.transcript = session.transcript || [];
      var last = session.transcript[session.transcript.length - 1];
      if (last && last.r === role && !last.done) {
        last.t = mergeUtterance(last.t, clean);
        last.done = Boolean(finished);
      } else {
        last = {r: role, t: clean, done: Boolean(finished)};
        session.transcript.push(last);
      }
      if (session.transcript.length > 24) {
        session.transcript = session.transcript.slice(-24);
      }
      try {
        call.sendMessage(JSON.stringify({r: role, t: last.t.slice(0, 400), f: last.done ? 1 : 0}));
      } catch (error) {
        // ignore
      }
    }

    function transcriptionFinished(block, payload) {
      if (!block) {
        return Boolean(payload.turnComplete || payload.generationComplete);
      }
      if (typeof block.finished === 'boolean') {
        return block.finished;
      }
      return Boolean(payload.turnComplete || payload.generationComplete);
    }

    voiceAIClient.addEventListener(Gemini.LiveAPIEvents.ServerContent, function (event) {
      var payload = (event && event.data && event.data.payload) || (event && event.data) || {};
      var input = payload.inputTranscription || payload.input_transcription || {};
      var output = payload.outputTranscription || payload.output_transcription || {};
      if (input.text && transcriptionFinished(input, payload)) {
        pushTranscript('p', input.text, true);
      }
      if (output.text) {
        pushTranscript('a', output.text, transcriptionFinished(output, payload));
      }
      if (payload.interrupted && voiceAIClient.clearMediaBuffer) {
        voiceAIClient.clearMediaBuffer();
      }
    });

    voiceAIClient.addEventListener(Gemini.LiveAPIEvents.ToolCall, function (event) {
      var functionCalls =
        (event && event.data && event.data.payload && event.data.payload.functionCalls) || [];
      var responses = [];
      functionCalls.forEach(function (fn) {
        if (!fn || !fn.id || !fn.name) {
          return;
        }
        if (fn.name !== 'submit_recovery_checkin') {
          responses.push({id: fn.id, name: fn.name, response: {error: 'unsupported_tool'}});
          return;
        }
        var checkin = validateCheckin(fn.args || {});
        if (!checkin) {
          responses.push({id: fn.id, name: fn.name, response: {error: 'invalid_arguments'}});
          return;
        }
        onSubmitted(true);
        var transcript = (session.transcript || [])
          .map(function (line) {
            return (line.r === 'p' ? 'Patient: ' : 'EIR: ') + line.t;
          })
          .join('\n')
          .slice(0, 1800);
        notify(session, 'CALL_COMPLETED', Object.assign({}, checkin, {transcript: transcript})).then(function () {
          setTimeout(function () {
            try {
              call.hangup();
            } catch (error) {
              VoxEngine.terminate();
            }
          }, 4000);
        });
        responses.push({
          id: fn.id,
          name: fn.name,
          response: {output: {ok: true, next: 'Give a brief closing statement, then end.'}},
        });
      });
      if (responses.length) {
        voiceAIClient.sendToolResponse({functionResponses: responses});
      }
    });
    return voiceAIClient;
  });
}

function baseSession(custom) {
  return {
    episodeId: custom.episodeId,
    correlationId: custom.correlationId,
    displayName: custom.displayName,
    transport: custom.transport,
    destinationUser: custom.destinationUser,
    callbackUrl: secret('EIR_CALLBACK_URL'),
    callbackToken: secret('EIR_CALLBACK_TOKEN'),
    destination: '',
    callerId: '',
    callId: '',
    transcript: [],
  };
}

function driveCall(session, call, timeoutMs) {
  var voiceAIClient;
  var submitted = false;
  var finished = false;

  function finish() {
    if (finished) {
      return;
    }
    finished = true;
    try {
      if (voiceAIClient) {
        voiceAIClient.close();
      }
    } catch (error) {
      // ignore
    }
    VoxEngine.terminate();
  }

  function markSubmitted(value) {
    if (value === true) {
      submitted = true;
    }
    return submitted;
  }

  session.callId = call.id();

  call.addEventListener(CallEvents.Failed, function (event) {
    var code = event && event.code;
    var state = NO_ANSWER_CODES[code] ? 'NO_ANSWER' : 'CALL_FAILED';
    notify(session, state, {failure_reason: state.toLowerCase()}).then(finish);
  });

  call.addEventListener(CallEvents.Disconnected, function () {
    if (!submitted) {
      notify(session, 'CALL_FAILED', {failure_reason: 'disconnected'}).then(finish);
      return;
    }
    finish();
  });

  call.addEventListener(CallEvents.Connected, async function () {
    await notify(session, 'CALL_CONNECTED');
    try {
      call.sendMessage(JSON.stringify({r: 'm', eid: session.episodeId}));
    } catch (error) {
      // ignore
    }
    startGeminiLive(session, call, markSubmitted)
      .then(function (client) {
        voiceAIClient = client;
      })
      .catch(function () {
        notify(session, 'CALL_FAILED', {failure_reason: 'gemini_setup'}).then(finish);
      });
    setTimeout(function () {
      if (!submitted) {
        notify(session, 'CALL_FAILED', {failure_reason: 'timeout'}).then(function () {
          try {
            call.hangup();
          } catch (error) {
            finish();
          }
        });
      }
    }, timeoutMs);
  });

  return finish;
}

function failStart(session) {
  if (session) {
    notify(session, 'CALL_FAILED', {failure_reason: 'scenario_error'}).then(function () {
      VoxEngine.terminate();
    });
    return;
  }
  VoxEngine.terminate();
}

VoxEngine.addEventListener(AppEvents.Started, function () {
  var session;
  var custom;
  var raw = String(VoxEngine.customData() || '').trim();
  if (!raw) {
    return;
  }
  try {
    custom = parseCustomData(raw);
  } catch (error) {
    return;
  }
  if (!custom.outbound) {
    return;
  }
  try {
    session = baseSession(custom);
    if (session.transport !== 'voximplant_user') {
      session.destination = secret('EIR_DEMO_PHONE_E164');
      session.callerId = secret('VOXIMPLANT_CALLER_ID_E164');
    }
    driveCall(session, startDestinationCall(session), TIMEOUT_MS_DIALLED);
    if (session.transport === 'voximplant_user') {
      notify(session, 'CALL_STARTED');
    }
  } catch (error) {
    failStart(session);
  }
});

// Inbound: the patient's browser dials the application over WebRTC. There is
// no PSTN leg, so no Caller ID and no destination number are involved.
VoxEngine.addEventListener(AppEvents.CallAlerting, function (event) {
  var session;
  var call = event && event.call;
  if (!call) {
    VoxEngine.terminate();
    return;
  }
  try {
    session = baseSession(parseCustomData(event.customData, 'webrtc'));
    driveCall(session, call, TIMEOUT_MS_WEBRTC);
    notify(session, 'CALL_STARTED');
    call.answer();
  } catch (error) {
    try {
      call.reject();
    } catch (inner) {
      // ignore
    }
    failStart(session);
  }
});
