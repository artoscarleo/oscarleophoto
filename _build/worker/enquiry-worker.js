/**
 * Enquiry handler for oscarleo.photography — Cloudflare Worker.
 *
 * The site is static (GitHub Pages), which cannot run code and cannot keep a
 * secret: anything in the repo or the page source is public. So the form POSTs
 * here instead, and this Worker holds the mail API key in its encrypted
 * environment. The key is never in the site, the repo, or the browser.
 *
 * It sends two emails per submission:
 *   1. the enquiry to contact@oscarleo.photography, with Reply-To set to the
 *      client so hitting Reply answers them directly;
 *   2. a confirmation to the client.
 *
 * DEPLOY
 *   Cloudflare dashboard → Workers & Pages → Create → Worker → paste this,
 *   then add the secret and variables listed under `env` below.
 *
 * REQUIRED SECRET (Settings → Variables → add, and tick "Encrypt")
 *   RESEND_API_KEY   your Resend API key (starts re_...)
 *
 * REQUIRED PLAIN VARIABLES
 *   MAIL_TO          contact@oscarleo.photography
 *   MAIL_FROM        Oscar Leo Photography <contact@oscarleo.photography>
 *                    (the domain must be verified in Resend, or delivery fails)
 *   ALLOW_ORIGIN     https://oscarleo.photography
 */

const MAX = { name: 120, email: 200, type: 120, date: 40, detail: 5000 };

// Per-IP rate limit, held in memory. A Worker isolate is short-lived and there
// are many of them, so this stops a burst from one source rather than being a
// guarantee. The honeypot on the form does most of the work; this is a backstop
// against someone hammering the endpoint directly.
const hits = new Map();
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 5;

function rateLimited(ip) {
  const now = Date.now();
  const seen = (hits.get(ip) || []).filter((t) => now - t < WINDOW_MS);
  seen.push(now);
  hits.set(ip, seen);
  if (hits.size > 5000) hits.clear();            // crude ceiling on memory
  return seen.length > MAX_PER_WINDOW;
}

const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const clean = (v, max) => String(v ?? '').trim().slice(0, max);

// Header injection guard: a newline in a header value can forge extra headers,
// and the client's address goes into Reply-To.
const safeHeader = (v) => clean(v, 200).replace(/[\r\n]/g, ' ');

function cors(env) {
  return {
    'Access-Control-Allow-Origin': env.ALLOW_ORIGIN || 'https://oscarleo.photography',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400'
  };
}

const json = (body, status, env) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...cors(env) }
  });

async function send(env, message) {
  // Copying a key out of a dashboard very often drags a newline or a stray
  // space along with it, which makes the Authorization header malformed and
  // comes back as a confusing "API key is invalid". Trim before use.
  const key = String(env.RESEND_API_KEY || '').trim();

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(message)
  });
  if (!res.ok) {
    // Shape only — never the value — so a bad paste can be diagnosed from the
    // logs without the secret ever being printed.
    const raw = String(env.RESEND_API_KEY || '');
    console.error('key shape', JSON.stringify({
      length: key.length,
      rawLength: raw.length,
      startsWithRe: key.startsWith('re_'),
      hadSurroundingWhitespace: raw !== key,
      hasInnerWhitespace: /\s/.test(key)
    }));
    throw new Error(`resend ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

function enquiryEmail(d, env) {
  const row = (k, v) => `
    <tr>
      <td style="padding:6px 16px 6px 0;color:#6b665c;font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;white-space:nowrap;vertical-align:top">${esc(k)}</td>
      <td style="padding:6px 0;color:#201e1a;font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">${esc(v) || '&mdash;'}</td>
    </tr>`;

  return {
    from: env.MAIL_FROM,
    to: [env.MAIL_TO],
    reply_to: safeHeader(d.email),               // Reply goes to the client
    subject: `New Photography Enquiry – ${clean(d.name, MAX.name) || 'Website'}`,
    html: `<div style="background:#faf9f6;padding:28px">
  <div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #e3dfd4;border-radius:10px;padding:28px">
    <p style="margin:0 0 4px;font:600 11px/1.4 -apple-system,sans-serif;letter-spacing:.09em;text-transform:uppercase;color:#8A7A55">New enquiry</p>
    <h1 style="margin:0 0 20px;font:600 22px/1.3 Georgia,serif;color:#201e1a">${esc(clean(d.name, MAX.name)) || 'Website enquiry'}</h1>
    <table style="width:100%;border-collapse:collapse">
      ${row('Name', clean(d.name, MAX.name))}
      ${row('Email', clean(d.email, MAX.email))}
      ${row('Type', clean(d.type, MAX.type))}
      ${row('Preferred date', clean(d.date, MAX.date) || 'not specified')}
    </table>
    <p style="margin:20px 0 6px;font:600 12px/1.4 -apple-system,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:#6b665c">Project</p>
    <p style="margin:0;white-space:pre-wrap;font:15px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#201e1a">${esc(clean(d.detail, MAX.detail)) || '&mdash;'}</p>
    <p style="margin:24px 0 0;padding-top:16px;border-top:1px solid #e3dfd4;font:13px/1.5 -apple-system,sans-serif;color:#94907f">Reply to this email to answer ${esc(clean(d.name, MAX.name)) || 'them'} directly.</p>
  </div>
</div>`,
    text: [
      `New enquiry from ${clean(d.name, MAX.name)}`,
      ``,
      `Name:           ${clean(d.name, MAX.name)}`,
      `Email:          ${clean(d.email, MAX.email)}`,
      `Type:           ${clean(d.type, MAX.type)}`,
      `Preferred date: ${clean(d.date, MAX.date) || 'not specified'}`,
      ``,
      `Project:`,
      clean(d.detail, MAX.detail) || '—'
    ].join('\n')
  };
}

function confirmationEmail(d, env) {
  const first = clean(d.name, MAX.name).split(/\s+/)[0] || 'there';
  return {
    from: env.MAIL_FROM,
    to: [clean(d.email, MAX.email)],
    reply_to: safeHeader(env.MAIL_TO),
    subject: 'Thank you for contacting Oscar Leo Photography',
    html: `<div style="background:#faf9f6;padding:28px">
  <div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #e3dfd4;border-radius:10px;overflow:hidden">
    <!-- The mark is baked onto an opaque cream band rather than sent as a
         transparent PNG. Gmail's dark mode inverts the white card behind it
         but leaves images alone, so a transparent dark-ink logo would vanish
         exactly where most people read their mail. Width and height are set
         so the space is reserved before the image loads, and the alt text
         carries the name for anyone whose client blocks images by default. -->
    <img src="https://oscarleo.photography/assets/img/logo/email-letterhead-1120.png"
         width="560" height="140" alt="Oscar Leo Photography"
         style="display:block;width:100%;max-width:560px;height:auto;border:0;outline:none;text-decoration:none">
    <div style="padding:28px 32px 32px">
    <p style="margin:0 0 18px;font:15px/1.65 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#201e1a">Hi ${esc(first)},</p>
    <p style="margin:0 0 16px;font:15px/1.65 -apple-system,sans-serif;color:#201e1a">Thank you for getting in touch with Oscar Leo Photography.</p>
    <p style="margin:0 0 16px;font:15px/1.65 -apple-system,sans-serif;color:#201e1a">Your enquiry has been received successfully, and I truly appreciate you taking the time to contact me.</p>
    <p style="margin:0 0 16px;font:15px/1.65 -apple-system,sans-serif;color:#201e1a">I will review the details of your request and get back to you as soon as possible.</p>
    <p style="margin:0 0 24px;font:15px/1.65 -apple-system,sans-serif;color:#201e1a">I look forward to hearing more about your plans and hopefully working together.</p>
    <p style="margin:0 0 4px;font:15px/1.65 -apple-system,sans-serif;color:#201e1a">Kind regards,</p>
    <p style="margin:0 0 18px;font:600 15px/1.65 Georgia,serif;color:#201e1a">Oscar Leo Photography</p>
    <p style="margin:0;padding-top:16px;border-top:1px solid #e3dfd4;font:13px/1.7 -apple-system,sans-serif;color:#6b665c">
      <a href="mailto:contact@oscarleo.photography" style="color:#8A7A55;text-decoration:none">contact@oscarleo.photography</a><br>
      <a href="https://oscarleo.photography" style="color:#8A7A55;text-decoration:none">oscarleo.photography</a>
    </p>
    </div>
  </div>
</div>`,
    text: [
      `Hi ${first},`, ``,
      `Thank you for getting in touch with Oscar Leo Photography.`, ``,
      `Your enquiry has been received successfully, and I truly appreciate you taking the time to contact me.`, ``,
      `I will review the details of your request and get back to you as soon as possible.`, ``,
      `I look forward to hearing more about your plans and hopefully working together.`, ``,
      `Kind regards,`, ``,
      `Oscar Leo Photography`,
      `contact@oscarleo.photography`,
      `https://oscarleo.photography`
    ].join('\n')
  };
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(env) });
    if (request.method !== 'POST') return json({ error: 'method' }, 405, env);

    // Only this site may post here.
    const origin = request.headers.get('Origin') || '';
    const allowed = env.ALLOW_ORIGIN || 'https://oscarleo.photography';
    if (origin && origin !== allowed) return json({ error: 'origin' }, 403, env);

    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    if (rateLimited(ip)) return json({ error: 'rate' }, 429, env);

    let d;
    try { d = await request.json(); } catch { return json({ error: 'body' }, 400, env); }

    // Honeypot, in case the browser check was bypassed. Answer 200 so a bot
    // learns nothing, and send nothing.
    if (clean(d.company, 200)) return json({ ok: true }, 200, env);

    const name = clean(d.name, MAX.name);
    const email = clean(d.email, MAX.email);
    if (!name || !email || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
      return json({ error: 'invalid' }, 400, env);
    }

    try {
      // The enquiry is what must not be lost — send and confirm it first.
      await send(env, enquiryEmail(d, env));
    } catch (err) {
      console.error('enquiry send failed', err);   // visible in Worker logs only
      return json({ error: 'send' }, 502, env);
    }

    try {
      await send(env, confirmationEmail(d, env));
    } catch (err) {
      // The enquiry already arrived. Failing the whole request here would tell
      // the visitor to send again and duplicate it, so this is logged and
      // swallowed instead.
      console.error('confirmation send failed', err);
    }

    return json({ ok: true }, 200, env);
  }
};
