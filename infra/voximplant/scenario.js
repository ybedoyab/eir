/**
 * EIR outbound recovery check-in.
 * Transport is selected from compact custom data; Gemini Live is shared.
 *
 * Custom data (max 200 bytes): {"eid","cid","n"[, "t":"user","u":"eir-preview-user"]}
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

function parseCustomData() {
  var raw = VoxEngine.customData() || '{}';
  var data = JSON.parse(raw);
  if (!data.eid || !data.cid) {
    throw new Error('invalid_custom_data');
  }
  var transport =
    data.t === 'user' || data.transport === 'voximplant_user' ? 'voximplant_user' : 'pstn';
  return {
    episodeId: String(data.eid),
    correlationId: String(data.cid),
    displayName: String(data.n || 'Alex').slice(0, 24),
    transport: transport,
    destinationUser: previewUsername(data.u || PREVIEW_USERNAME),
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

function playNativeGreeting(call, text) {
  try {
    if (typeof VoiceList !== 'undefined' && VoiceList.Google && VoiceList.Google.en_US_Neural2_F) {
      call.say(text, {language: VoiceList.Google.en_US_Neural2_F});
      return true;
    }
  } catch (error) {
    // fall through
  }
  try {
    call.say(text);
    return true;
  } catch (error) {
    return false;
  }
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

function startGeminiLive(session, call, onSubmitted, options) {
  options = options || {};
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
      if (options.alreadyGreeted) {
        voiceAIClient.sendRealtimeInput({
          text:
            'The patient already heard your greeting. Do not repeat it. ' +
            'Wait for their reply, then continue the recovery check-in.',
        });
        return;
      }
      voiceAIClient.sendRealtimeInput({
        text: 'Speak this greeting now, then wait for the patient: ' + greetingText(session),
      });
    }

    voiceAIClient.addEventListener(Gemini.LiveAPIEvents.SetupComplete, startConversation);
    if (Gemini.Events && Gemini.Events.WebSocketMediaStarted) {
      voiceAIClient.addEventListener(Gemini.Events.WebSocketMediaStarted, bindCallAudio);
    }

    voiceAIClient.addEventListener(Gemini.LiveAPIEvents.ServerContent, function (event) {
      var payload = (event && event.data && event.data.payload) || {};
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
        notify(session, 'CALL_COMPLETED', checkin).then(function () {
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

VoxEngine.addEventListener(AppEvents.Started, async function () {
  var session;
  var call;
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

  try {
    var custom = parseCustomData();
    session = {
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
    };

    if (session.transport !== 'voximplant_user') {
      session.destination = secret('EIR_DEMO_PHONE_E164');
      session.callerId = secret('VOXIMPLANT_CALLER_ID_E164');
    }

    call = startDestinationCall(session);
    session.callId = call.id();
    if (session.transport === 'voximplant_user') {
      notify(session, 'CALL_STARTED');
    }

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
      var greeted = playNativeGreeting(call, greetingText(session));
      var geminiConnecting = false;

      function connectGemini() {
        if (geminiConnecting || voiceAIClient) {
          return;
        }
        geminiConnecting = true;
        startGeminiLive(session, call, markSubmitted, {alreadyGreeted: greeted})
          .then(function (client) {
            voiceAIClient = client;
          })
          .catch(function () {
            notify(session, 'CALL_FAILED', {failure_reason: 'gemini_setup'}).then(finish);
          });
      }

      if (greeted) {
        call.addEventListener(CallEvents.PlaybackFinished, connectGemini);
        setTimeout(connectGemini, 10000);
      } else {
        connectGemini();
      }
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
      }, 90000);
    });
  } catch (error) {
    if (session) {
      notify(session, 'CALL_FAILED', {failure_reason: 'scenario_error'}).then(finish);
      return;
    }
    finish();
  }
});
