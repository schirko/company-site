// The Contact Us page (2026-10-30; Scott chose B of notes/site-contact-B-*-2026-10-30.png). The form is sent to
// Web3Forms, which emails it to the company address. With JavaScript the page sends it and says how it went;
// without, the browser posts it to Web3Forms, which shows its own thank-you page. Nothing is kept on this site.
"use strict";
(() => {
  const form = document.getElementById("contact-form");
  if (!form) return;
  const status = document.getElementById("cf-status");
  const button = form.querySelector('button[type="submit"]');
  const say = (text, kind) => { status.textContent = text; status.className = `cf-status ${kind}`; status.hidden = false; };
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = Object.fromEntries(new FormData(form));
    if (data.botcheck) return;                       // the hidden box only a robot ticks
    data.subject = `Cornerpost Logic: ${data.about || "a message"}`;
    button.disabled = true;
    button.textContent = "Sending…";
    try {
      const r = await fetch(form.action, {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(data),
      });
      const answer = await r.json().catch(() => ({}));
      if (!r.ok || !answer.success) throw new Error(answer.message || "");
      form.reset();
      say("Thanks, your message is on its way. We'll write back to the email you gave.", "ok");
    } catch {
      say("It didn't go through. Please try again in a minute, or email us at the address on the right.", "bad");
    } finally {
      button.disabled = false;
      button.textContent = "Send Message";
    }
  });
})();
