/**
 * EIR outbound PSTN recovery check-in.
 * Voximplant → Gemini Live (Vertex AI) → authenticated EIR callback.
 *
 * Custom data (max 200 bytes): {"eid","cid","n"}
 * Destination, caller ID, callback token, and Vertex credentials come from
 * VoxEngine secret storage. Do not log phones, tokens, or transcripts.
 */
require(Modules.Gemini);

var GEMINI_LIVE_MODEL = 'gemini-live-2.5-flash-native-audio';
var GEMINI_LIVE_VOICE = 'Sulafat';
var VERTEX_PROJECT = 'eir-ata';
var VERTEX_LOCATION = 'us-central1';
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

function parseCustomData() {
  var raw = VoxEngine.customData() || '{}';
  var data = JSON.parse(raw);
  if (!data.eid || !data.cid) {
    throw new Error('invalid_custom_data');
  }
  return {
    episodeId: String(data.eid),
    correlationId: String(data.cid),
    displayName: String(data.n || 'Alex').slice(0, 24),
  };
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

  try {
    var custom = parseCustomData();
    session = {
      episodeId: custom.episodeId,
      correlationId: custom.correlationId,
      displayName: custom.displayName,
      callbackUrl: secret('EIR_CALLBACK_URL'),
      callbackToken: secret('EIR_CALLBACK_TOKEN'),
      destination: secret('EIR_DEMO_PHONE_E164'),
      callerId: secret('VOXIMPLANT_CALLER_ID_E164'),
      callId: '',
    };

    call = VoxEngine.callPSTN(session.destination, session.callerId);
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
      var credentials = JSON.parse(secret('EIR_GEMINI_VERTEX_CREDENTIALS'));
      voiceAIClient = await Gemini.createLiveAPIClient({
        credentials: credentials,
        model: GEMINI_LIVE_MODEL,
        backend: Gemini.Backend.VERTEX_AI,
        project: VERTEX_PROJECT,
        location: VERTEX_LOCATION,
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
          if (!submitted) {
            notify(session, 'CALL_FAILED', {failure_reason: 'gemini_closed'}).then(finish);
          }
        },
      });

      voiceAIClient.addEventListener(Gemini.LiveAPIEvents.SetupComplete, function () {
        VoxEngine.sendMediaBetween(call, voiceAIClient);
        var intro =
          'Hi ' +
          session.displayName +
          ", this is EIR, the automated recovery assistant following up after your recent visit. " +
          'Is now a good time for a quick recovery check-in?';
        voiceAIClient.sendClientContent({
          turns: [{role: 'user', parts: [{text: 'Begin the call by saying: ' + intro}]}],
          turnComplete: true,
        });
      });

      voiceAIClient.addEventListener(Gemini.LiveAPIEvents.ServerContent, function (event) {
        var payload = (event && event.data && event.data.payload) || {};
        if (payload.interrupted && voiceAIClient.clearMediaBuffer) {
          voiceAIClient.clearMediaBuffer();
        }
      });

      voiceAIClient.addEventListener(Gemini.LiveAPIEvents.ToolCall, function (event) {
        var functionCalls = (event && event.data && event.data.payload && event.data.payload.functionCalls) || [];
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
          submitted = true;
          notify(session, 'CALL_COMPLETED', checkin).then(function () {
            setTimeout(function () {
              try {
                call.hangup();
              } catch (error) {
                finish();
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
