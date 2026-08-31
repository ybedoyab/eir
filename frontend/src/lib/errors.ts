export const ERROR_MESSAGES = {
  generic: "Something went wrong. Please try again.",
  apiUnavailable: "The API is currently unavailable.",
  login: "Sign in failed. Use the demo password shown for each role.",
  demoUsers: "Could not load demo users.",
  patients: "Could not load patients.",
  patient: "Could not load patient.",
  patientHome: "Could not load your home.",
  appointments: "Could not load appointments.",
  appointmentSave: "Could not save appointment.",
  appointmentCancel: "Could not cancel appointment.",
  assistant: "Could not start the assistant.",
  message: "Could not send the message.",
  recovery: "Could not load recovery data.",
  followUp: "Could not start the follow-up.",
  reviews: "Could not load reviews.",
  reviewResolve: "Could not resolve the review.",
  schedule: "Could not load the schedule.",
  clinician: "Could not load the clinician workspace.",
  operations: "Could not load operations.",
  inventory: "Could not load inventory.",
  fleet: "Could not load the fleet.",
  supplyCase: "Could not load the supply case.",
  purchaseAuthorization: "Could not authorize the purchase order.",
  delivery: "Could not record the delivery.",
  demoRefresh: "Could not refresh the demo.",
  demoStart: "Could not start the demo.",
  demoFastForward: "Could not fast-forward the demo.",
  attackSimulation: "Could not run the attack simulation.",
  concerningSignal: "Could not send the concerning signal.",
  voiceRetry: "Could not retry the voice check-in.",
  voiceOpen: "Could not open the in-page voice check-in.",
  video: "Could not request a new recovery video.",
  recoveryCreate: "Could not create the recovery episode.",
  request: "The request failed.",
} as const;

export function getErrorMessage(error: unknown, fallback: string = ERROR_MESSAGES.generic): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

export class ApiError extends Error {
  constructor(
    readonly path: string,
    readonly status: number,
  ) {
    super(`${path} failed (${status})`);
    this.name = "ApiError";
  }
}
