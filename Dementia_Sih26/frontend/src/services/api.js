// ── API service layer ─────────────────────────────────────────────────────────
const BASE = "/api";
import { cacheKey, enqueue, getCached, setCached } from "../utils/offlineDb";
import { getIsOnline, syncNow } from "../utils/syncManager";

// ── Token / session helpers ───────────────────────────────────────────────────
export const getToken   = () => sessionStorage.getItem("neuroaid_token");
export const getUser    = () => { const u = sessionStorage.getItem("neuroaid_user"); return u ? JSON.parse(u) : null; };
export const isLoggedIn = () => !!getToken();

export function saveSession(token, user) {
  sessionStorage.setItem("neuroaid_token", token);
  sessionStorage.setItem("neuroaid_user", JSON.stringify(user));
}
export function clearSession() {
  sessionStorage.removeItem("neuroaid_token");
  sessionStorage.removeItem("neuroaid_user");
}


// ── Core request ──────────────────────────────────────────────────────────────
async function request(method, path, body, requiresAuth = false) {
  const headers = { "Content-Type": "application/json" };
  if (requiresAuth) {
    const token = getToken();
    if (!token) throw new Error("Not authenticated. Please log in.");
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    if (res.status === 401 && requiresAuth) {
      clearSession();
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Auth API ──────────────────────────────────────────────────────────────────

/** Register a new user. role = "patient" | "doctor" | "caregiver" */
export async function register({ full_name, email, password, role, age, gender, phone, license_number, specialization, hospital, location, years_experience, consultation_mode, bio, max_patients }) {
  const data = await request("POST", "/auth/register", { full_name, email, password, role, age, gender, phone, license_number, specialization, hospital, location, years_experience, consultation_mode, bio, max_patients });
  saveSession(data.token, data.user);
  return data;
}

/** Login. role = "patient" | "doctor" | "caregiver" */
export async function login(email, password, role = "patient") {
  const data = await request("POST", "/auth/login", { email, password, role });
  saveSession(data.token, data.user);
  return data;
}

/** Logout current user. */
export async function logout() {
  try { await request("POST", "/auth/logout", null, true); } finally { clearSession(); }
}

/** Get current user profile. */
export async function fetchMe() {
  const data = await request("GET", "/auth/me", null, true);
  sessionStorage.setItem("neuroaid_user", JSON.stringify(data.user));
  return data.user;
}

/** Doctors & Care Team — get assigned patients. */
export async function getPatients() {
  const data = await request("GET", "/auth/patients", null, true);
  return data.patients;
}

// ── Assessment API ────────────────────────────────────────────────────────────
export const submitAnalysis = (payload) => request("POST", "/analyze", payload, true);

/** Get current patient's own past results */
export async function getMyResults() {
  const data = await request("GET", "/results/my", null, true);
  return data.results; // array, newest last
}

/** Doctor only — get a specific patient's results (consent-checked) */
export async function getPatientResults(patientId) {
  const data = await request("GET", `/results/patient/${patientId}`, null, true);
  return data.results;
}

// ── Consent Management API ────────────────────────────────────────────────────
export async function getConsent() {
  return request("GET", "/consent", null, true);
}

export async function updateConsent(payload) {
  return request("PUT", "/consent", payload, true);
}

export async function getAuditLogs(limit = 50) {
  return request("GET", `/auth/audit-logs?limit=${limit}`, null, true);
}

// ── Messaging ────────────────────────────────────────────────────────────────
export async function sendMessage(recipientId, text) {
  return request("POST", "/messages/send", { recipient_id: recipientId, text }, true);
}
export async function getMessages(otherUserId) {
  const data = await request("GET", `/messages/${otherUserId}`, null, true);
  return data.messages;
}
export async function deleteMessage(messageId) {
  return request("DELETE", `/messages/${messageId}`, null, true);
}
export async function getConversations() {
  const data = await request("GET", "/conversations", null, true);
  return data.conversations;
}
export async function getUnreadCount() {
  const data = await request("GET", "/messages/unread/count", null, true);
  return data.count;
}

export async function getDoctors() {
  const data = await request("GET", "/auth/doctors", null, true);
  return data.doctors;
}

export async function getMyDoctor() {
  const data = await request("GET", "/auth/doctors/my-doctor", null, true);
  return data;
}

export async function enrollWithDoctor(doctorId) {
  return request("POST", "/auth/doctors/enroll", { doctor_id: doctorId }, true);
}

export async function getPendingRequests() {
  const data = await request("GET", "/auth/doctors/pending-requests", null, true);
  return data.pending_requests;
}

export async function approvePatient(patientId, action) {
  return request("POST", "/auth/doctors/approve", { patient_id: patientId, action }, true);
}

// ── Educational RAG Chat ─────────────────────────────────────────────────────
export async function submitChat(question, userContext = {}) {
  return request("POST", "/chat", { question, user_context: userContext }, false);
}

// ── Cognitive Games API (SIH PS 26003) ───────────────────────────────────────
export async function getGamesList() {
  return request("GET", "/games", null, false);
}

export async function getGameConfig(gameId) {
  return request("GET", `/games/${gameId}/config`, null, false);
}

export async function submitGameSession(payload) {
  const token = getToken();
  const actionId = crypto.randomUUID();
  const isOnline = getIsOnline();
  const optimistic = { session_id: actionId, ...payload, score: payload.score || Math.max(40, 100 - (payload.mistakes_count || 0) * 12), stars: 3, stars_label: "3/3 Stars", feedback_message: "Saved safely on this device.", cognitive_domain: "Cognitive Training", timestamp: new Date().toISOString(), offline: !isOnline };
  if (!isOnline) {
    await enqueue({ id: actionId, type: "GAME_SESSION", payload: { ...payload, client_action_id: actionId } });
    const user = getUser(); const key = cacheKey(user?.id, "game-history");
    const history = await getCached(key, []); await setCached(key, [optimistic, ...history]);
    syncNow(); return optimistic;
  }
  return request("POST", "/games/session", { ...payload, client_action_id: actionId }, !!token);
}

export const getCareDashboard = () => request("GET", "/dashboard/patients", null, true);
export const getCarePatientDashboard = patientId => request("GET", `/dashboard/patient/${patientId}`, null, true);
export const getCaregiverAlerts = patientId => request("GET", `/dashboard/patient/${patientId}/alerts`, null, true);
export const reviewCaregiverAlert = (patientId, alertId, status = "reviewed") =>
  request("POST", `/dashboard/patient/${patientId}/alerts/${alertId}/review`, { status }, true);

// ── Patient-Caregiver Relationship Management ────────────────────────────────
export const getMyCaregivers = () => request("GET", "/caregivers/my-caregivers", null, true);
export const assignCaregiver = caregiverIdentity =>
  request("POST", "/caregivers/assign", { caregiver_identity: caregiverIdentity }, true);
export const revokeCaregiver = caregiverId =>
  request("POST", "/caregivers/revoke", { caregiver_id: caregiverId }, true);

export async function getGameHistory() {
  const token = getToken();
  const key = cacheKey(getUser()?.id, "game-history");
  try { const value = await request("GET", "/games/history", null, !!token); await setCached(key, value.sessions || []); return value; }
  catch (error) { if (!getIsOnline()) return { sessions: await getCached(key, []) }; throw error; }
}

export async function getGameStats() {
  const token = getToken();
  return request("GET", "/games/stats", null, !!token);
}

export async function getReminders() {
  const key = cacheKey(getUser()?.id, "reminders");
  try { const value = await request("GET", "/reminders", null, true); await setCached(key, value); return value; }
  catch (error) { if (!getIsOnline()) return getCached(key, []); throw error; }
}

export async function completeReminder(reminderId) {
  return toggleReminderStatus(reminderId, "completed");
}

export async function toggleReminderStatus(reminderId, targetStatus) {
  const actionId = crypto.randomUUID();
  const key = cacheKey(getUser()?.id, "reminders");
  const newStatus = targetStatus || "completed";

  const optimisticUpdate = async () => {
    const reminders = await getCached(key, []);
    const item = reminders.find(r => r.id === reminderId);
    if (item) {
      item.status = newStatus;
      if (newStatus === "completed") {
        item.last_completed_at = new Date().toISOString();
      } else {
        delete item.last_completed_at;
      }
      await setCached(key, reminders);
    }
    return item;
  };

  if (!getIsOnline()) {
    const item = await optimisticUpdate();
    await enqueue({
      id: actionId,
      type: newStatus === "completed" ? "REMINDER_COMPLETE" : "REMINDER_UPDATE",
      payload: { reminder_id: reminderId, status: newStatus }
    });
    syncNow();
    return item || { id: reminderId, status: newStatus, offline: true };
  }

  try {
    let item;
    if (newStatus === "completed") {
      item = await request("POST", `/reminders/${reminderId}/complete`, null, true);
    } else {
      item = await request("PUT", `/reminders/${reminderId}`, { status: "pending" }, true);
    }
    await optimisticUpdate();
    return item;
  } catch (err) {
    const item = await optimisticUpdate();
    return item || { id: reminderId, status: newStatus };
  }
}

export async function getMemoryItems() {
  const key = cacheKey(getUser()?.id, "memory-items");
  try { const value = await request("GET", "/memory-bank", null, true); await setCached(key, value); return value; }
  catch (error) { if (!getIsOnline()) return getCached(key, []); throw error; }
}

export async function getGameRecommendation(gameId) {
  const token = getToken();
  return request("GET", `/games/${gameId}/recommended-level`, null, !!token);
}

// ── Deterministic SIH Demo API ────────────────────────────────────────────────
export async function resetAndSeedDemo() {
  return request("POST", "/demo/reset-and-seed", null, false);
}

// ── Rhythm & Recall API ───────────────────────────────────────────────────────
export async function getRhythmMusic() {
  return request("GET", "/rhythm/music", null, false);
}

export async function getRhythmMusicPersonalized(patientId) {
  const path = patientId ? `/rhythm/music/personalized?patient_id=${patientId}` : "/rhythm/music/personalized";
  return request("GET", path, null, true);
}

export async function saveRhythmSession(sessionData) {
  return request("POST", "/rhythm/sessions", sessionData, true);
}

export async function getRhythmSessions(patientId, limit = 20) {
  const query = patientId ? `?patient_id=${patientId}&limit=${limit}` : `?limit=${limit}`;
  return request("GET", `/rhythm/sessions${query}`, null, true);
}

export async function saveRhythmRound(sessionId, roundData) {
  return request("POST", `/rhythm/sessions/${sessionId}/round`, roundData, true);
}

export async function getRhythmAnalytics(patientId) {
  const path = patientId ? `/rhythm/analytics?patient_id=${patientId}` : "/rhythm/analytics";
  return request("GET", path, null, true);
}
export async function saveRhythmPreferences(preferences) {
  return request("POST", "/rhythm/preferences", preferences, true);
}

export async function getRhythmPreferences() {
  return request("GET", "/rhythm/preferences", null, true);
}

export async function deleteRhythmSession(sessionId) {
  return request("DELETE", `/rhythm/sessions/${sessionId}`, null, true);
}
