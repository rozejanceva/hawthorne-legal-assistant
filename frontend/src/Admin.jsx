import React, { useEffect, useState } from "react";
import { api } from "./api.js";

const formatSlot = (value) => new Intl.DateTimeFormat("en", {
  weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
}).format(new Date(value));

export function AdminApp() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [appointments, setAppointments] = useState([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadAppointments() {
    const rows = await api("/admin/appointments");
    setAppointments(rows);
    setAuthenticated(true);
  }

  useEffect(() => {
    api("/admin/session").then((data) => {
      if (data.authenticated) loadAppointments().catch(() => setAuthenticated(false));
    }).catch(() => {});
  }, []);

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      await api("/admin/login", { method: "POST", body: JSON.stringify({ username, password }) });
      setPassword("");
      await loadAppointments();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await api("/admin/logout", { method: "POST", body: "{}" });
    setAuthenticated(false);
    setAppointments([]);
  }

  if (!authenticated) {
    return (
      <main className="admin-page">
        <form className="booking-card admin-card" onSubmit={login}>
          <p className="eyebrow">Office access</p>
          <h1>Sign in</h1>
          <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></label>
          {notice && <p className="notice" role="status">{notice}</p>}
          <button className="button dark" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          <a className="header-link" href="/">Back to site</a>
        </form>
      </main>
    );
  }

  return (
    <main className="admin-page">
      <header className="admin-header">
        <h1>Appointments</h1>
        <div>
          <button className="button dark" type="button" onClick={loadAppointments}>Refresh</button>
          <button className="button primary" type="button" onClick={logout}>Sign out</button>
        </div>
      </header>
      {appointments.length === 0 ? <p>No appointments yet.</p> : (
        <table className="admin-table">
          <thead>
            <tr><th>When</th><th>Client</th><th>Type</th><th>Calendar</th></tr>
          </thead>
          <tbody>
            {appointments.map((row) => (
              <tr key={row.id}>
                <td>{formatSlot(row.starts_at)} – {formatSlot(row.ends_at)}</td>
                <td>{row.client_name}<br /><span>{row.client_email}</span></td>
                <td>{row.consultation_type}</td>
                <td>{row.calendar_event_id.startsWith("demo-") ? "Demo" : "Google"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
