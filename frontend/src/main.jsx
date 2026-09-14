import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { api, apiDate } from "./api.js";
import { AdminApp } from "./Admin.jsx";

const consultationTypes = [
  ["Initial Consultation", "30 minutes", "A first conversation about your situation."],
  ["Follow-up Consultation", "30 minutes", "Continue an existing discussion."],
  ["Detailed Case Consultation", "60 minutes", "More time for a complex matter."],
];

const formatSlot = (value) => new Intl.DateTimeFormat("en", {
  weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit",
}).format(new Date(value));

function ChatWidget({ officeLabel, slotInterval }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: "bot", text: "Hello! I’m the virtual scheduling assistant. How can I help today?" }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showBooking, setShowBooking] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", type: consultationTypes[0][0], preferred: "" });
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState("");

  async function sendMessage(event) {
    event?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setMessages((all) => [...all, { role: "user", text }]);
    setInput("");
    setLoading(true);
    try {
      const data = await api("/chat", { method: "POST", body: JSON.stringify({ message: text }) });
      setMessages((all) => [...all, { role: "bot", text: data.message }]);
    } catch {
      setMessages((all) => [...all, { role: "bot", text: "I’m sorry, I couldn’t connect right now. Please try again." }]);
    } finally {
      setLoading(false);
    }
  }

  async function checkSlots(event) {
    event.preventDefault();
    if (!form.preferred) return;
    setLoading(true);
    try {
      const data = await api("/availability", {
        method: "POST",
        body: JSON.stringify({ consultation_type: form.type, preferred_start: apiDate(form.preferred) }),
      });
      const nextSlots = data.slots || [];
      setSlots(nextSlots);
      setSelectedSlot(nextSlots[0] || "");
      setMessages((all) => [...all, { role: "bot", text: data.available ? "That time is available. Select it below to confirm." : "Here are the nearest available appointment times." }]);
    } catch {
      setMessages((all) => [...all, { role: "bot", text: "I couldn’t check availability. Please try again." }]);
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    if (!form.name || !form.email || !selectedSlot) return;
    setLoading(true);
    try {
      const data = await api("/appointments", {
        method: "POST",
        body: JSON.stringify({
          client_name: form.name,
          client_email: form.email,
          consultation_type: form.type,
          starts_at: selectedSlot,
        }),
      });
      setMessages((all) => [...all, { role: "bot", text: `Confirmed — your appointment is booked for ${formatSlot(data.starts_at)}.` }]);
      setSlots([]);
      setSelectedSlot("");
    } catch (error) {
      setMessages((all) => [...all, { role: "bot", text: error.message || "That time is no longer available. Please choose another." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-widget">
      {open && (
        <section className="chat-panel" aria-label="Scheduling assistant">
          <header>
            <div><strong>Hawthorne Legal</strong><span>Scheduling assistant</span></div>
            <button className="close-chat" type="button" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </header>
          <div className="chat-messages">
            {messages.map((message, index) => <p className={`message ${message.role}`} key={index}>{message.text}</p>)}
            {loading && <p className="message bot">Thinking…</p>}
          </div>
          {!showBooking ? (
            <button className="chat-book" type="button" onClick={() => { setShowBooking(true); setMessages((all) => [...all, { role: "bot", text: "Of course. Please enter your details and preferred time below." }]); }}>Schedule a consultation</button>
          ) : (
            <form className="chat-booking" onSubmit={checkSlots}>
              <input required aria-label="Your name" placeholder="Your name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <input required aria-label="Email address" type="email" placeholder="Email address" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <select aria-label="Consultation type" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {consultationTypes.map(([type, duration]) => <option key={type} value={type}>{type} — {duration}</option>)}
              </select>
              <input required aria-label="Preferred date and time" type="datetime-local" step={slotInterval * 60} value={form.preferred} onChange={(e) => setForm({ ...form, preferred: e.target.value })} />
              <button className="chat-book" disabled={loading}>Check available times</button>
              {slots.map((slot) => (
                <label className="chat-slot" key={slot}>
                  <input type="radio" name="chat-slot" checked={selectedSlot === slot} onChange={() => setSelectedSlot(slot)} /> {formatSlot(slot)}
                </label>
              ))}
              {slots.length > 0 && <button className="chat-confirm" type="button" disabled={loading} onClick={confirm}>Confirm appointment</button>}
            </form>
          )}
          <form className="chat-input" onSubmit={sendMessage}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about appointments…" />
            <button disabled={loading} aria-label="Send message">↑</button>
          </form>
        </section>
      )}
      <button className="chat-toggle" type="button" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>{open ? "×" : "✦"}</span>{open ? "Close" : "Chat with us"}
      </button>
    </div>
  );
}

function App() {
  const [form, setForm] = useState({ name: "", email: "", type: consultationTypes[0][0], preferred: "" });
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [officeLabel, setOfficeLabel] = useState("Europe/Skopje");
  const [slotInterval, setSlotInterval] = useState(30);

  useEffect(() => {
    api("/public-config").then((data) => {
      setOfficeLabel(data.timezone);
      setSlotInterval(data.slot_interval_minutes || 30);
    }).catch(() => {});
  }, []);

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  async function checkAvailability(event) {
    event.preventDefault();
    if (!form.preferred) return setNotice("Choose your preferred date and time first.");
    setBusy(true);
    setNotice("");
    setSlots([]);
    setSelectedSlot("");
    try {
      const data = await api("/availability", {
        method: "POST",
        body: JSON.stringify({ consultation_type: form.type, preferred_start: apiDate(form.preferred) }),
      });
      const nextSlots = data.slots || [];
      setSlots(nextSlots);
      setSelectedSlot(nextSlots[0] || "");
      setNotice(data.available ? "Your requested time is available. Confirm it below." : "Your requested time is unavailable. Please choose one of these available times.");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function confirmBooking() {
    if (!form.name || !form.email || !selectedSlot) return setNotice("Enter your name and email, then select an available time.");
    setBusy(true);
    setNotice("");
    try {
      const data = await api("/appointments", {
        method: "POST",
        body: JSON.stringify({
          client_name: form.name,
          client_email: form.email,
          consultation_type: form.type,
          starts_at: selectedSlot,
        }),
      });
      setNotice(`Confirmed — your ${data.consultation_type.toLowerCase()} is booked for ${formatSlot(data.starts_at)}.`);
      setSlots([]);
      setSelectedSlot("");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="site-header">
        <a className="brand" href="#top"><span>H</span> Hawthorne Legal</a>
        <a className="header-link" href="#book">Schedule a consultation</a>
      </header>
      <main id="top">
        <section className="hero">
          <p className="eyebrow">Trusted counsel. Clear next steps.</p>
          <h1>Legal guidance begins with a conversation.</h1>
          <p className="hero-copy">Arrange a confidential consultation with our office at a time that works for you.</p>
          <a className="button primary" href="#book">Book a consultation <span>→</span></a>
          <div className="trust-row"><span>Confidential consultations</span><span>•</span><span>Thoughtful, client-first service</span></div>
        </section>
        <section className="practice" aria-label="Our approach">
          <p className="eyebrow">Our approach</p>
          <h2>Practical legal support, delivered with care.</h2>
          <p>Every matter starts by listening. Our office provides a calm, focused setting to discuss your options and determine the right next step.</p>
        </section>
        <section className="booking-section" id="book">
          <div className="booking-intro">
            <p className="eyebrow">Online scheduling</p>
            <h2>Find a time to talk.</h2>
            <p>Choose your consultation type and preferred time. We’ll show only available appointment times—never our private calendar.</p>
            <p className="disclaimer">This scheduling assistant cannot give legal advice or assess your case. Appointment times are in {officeLabel}.</p>
          </div>
          <form className="booking-card" onSubmit={checkAvailability}>
            <div className="field-row">
              <label>Your name<input required value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="Jane Smith" /></label>
              <label>Email address<input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} placeholder="jane@example.com" /></label>
            </div>
            <label>Consultation type
              <select value={form.type} onChange={(e) => update("type", e.target.value)}>
                {consultationTypes.map(([type, duration]) => <option key={type} value={type}>{type} — {duration}</option>)}
              </select>
            </label>
            <label>Preferred date and time
              <input required type="datetime-local" step={slotInterval * 60} value={form.preferred} onChange={(e) => update("preferred", e.target.value)} />
            </label>
            <p className="field-hint">Enter the time you want in the office timezone ({officeLabel}). Seconds are not used.</p>
            <button className="button primary" disabled={busy} type="submit">{busy ? "Checking…" : "Check availability"}</button>
            {notice && <p className="notice" role="status">{notice}</p>}
            {slots.length > 0 && (
              <div className="slots">
                <h3>Available times</h3>
                {slots.map((slot) => (
                  <label className="slot" key={slot}>
                    <input type="radio" name="slot" checked={selectedSlot === slot} onChange={() => setSelectedSlot(slot)} />
                    <span>{formatSlot(slot)}</span>
                  </label>
                ))}
                <button className="button dark" disabled={busy} type="button" onClick={confirmBooking}>{busy ? "Confirming…" : "Confirm appointment"}</button>
              </div>
            )}
          </form>
        </section>
      </main>
      <footer>
        <span>© {new Date().getFullYear()} Hawthorne Legal</span>
        <a className="footer-admin" href="/admin">Office login</a>
      </footer>
      <ChatWidget officeLabel={officeLabel} slotInterval={slotInterval} />
    </>
  );
}

const root = createRoot(document.getElementById("root"));
if (window.location.pathname.startsWith("/admin")) {
  root.render(<AdminApp />);
} else {
  root.render(<App />);
}
