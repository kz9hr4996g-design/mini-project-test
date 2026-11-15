# mini-project-test
## WhatsApp alerts

Each CIO decision (INVEST / MONITOR by default) is pushed to WhatsApp through Twilio.

1. Create a Twilio account → Messaging → Try it out → **Send a WhatsApp message**.
   From your phone, send the join code (e.g. `join <two-words>`) to `+1 415 523 8886`.
2. In `.env` set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` and `WHATSAPP_TO`
   (comma-separated, E.164 format, e.g. `+447700900123`).
   Optional: `WHATSAPP_VERDICTS=INVEST` to get only INVEST calls.
3. `docker compose up -d --build`, then send a test message:
   `curl -X POST http://localhost:8000/api/v1/notifications/whatsapp/test`

Leaving the Twilio settings blank turns alerts off. For production, swap the sandbox
sender for your own approved WhatsApp number in `TWILIO_WHATSAPP_FROM`.
