const fs = require('fs');
const path = require('path');
const { authenticate } = require('@google-cloud/local-auth');
const { google } = require('googleapis');

const SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'];
const TOKEN_PATH = path.join(__dirname, 'token.json');
const CREDENTIALS_PATH = path.join(__dirname, 'credentials.json');

async function authorize() {
  const client = await authenticate({
    scopes: SCOPES,
    keyfilePath: CREDENTIALS_PATH,
  });

  // 🔥 FORCE SAVE TOKEN
  fs.writeFileSync(TOKEN_PATH, JSON.stringify(client.credentials, null, 2));
  console.log("✅ Token saved at:", TOKEN_PATH);

  return client;
}

async function listEmails() {
  const auth = await authorize();
  const gmail = google.gmail({ version: 'v1', auth });

  const res = await gmail.users.messages.list({
    userId: 'me',
    maxResults: 5,
  });

  const messages = res.data.messages || [];

  console.log('📧 Emails:');

  for (let msg of messages) {
    const email = await gmail.users.messages.get({
      userId: 'me',
      id: msg.id,
    });

    const headers = email.data.payload.headers;

    const subject = headers.find(h => h.name === 'Subject')?.value;
    const from = headers.find(h => h.name === 'From')?.value;

    console.log("📩 From:", from);
    console.log("📝 Subject:", subject);
    console.log("----");
  }
}

listEmails();