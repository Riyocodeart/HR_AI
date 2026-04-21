require("dotenv").config();

const fs = require("fs");
const { LinkedInProfileScraper } = require("linkedin-profile-scraper");

console.log("ENV COOKIE:", process.env.LI_AT);

// ❗ Stop immediately if cookie missing
if (!process.env.LI_AT) {
  throw new Error("❌ LI_AT not loaded from .env");
}

const delay = (ms) => new Promise(res => setTimeout(res, ms));

(async () => {
  console.log("🚀 Starting scraper...");

  const scraper = new LinkedInProfileScraper({
    sessionCookieValue: process.env.LI_AT,
    keepAlive: true,
    headless: false
  });

  await scraper.setup();

  const profileUrls = [
    "https://www.linkedin.com/in/ananddubey104/",
    "https://www.linkedin.com/in/anujhsawant/"
  ];

  let results = [];

  for (let i = 0; i < profileUrls.length; i++) {
    const url = profileUrls[i];

    console.log(`\n🔍 Scraping (${i + 1}/${profileUrls.length}): ${url}`);

    try {
      const data = await scraper.run(url);

      if (!data.userProfile.fullName) {
        console.log("⚠️ Blocked / Not logged in:", url);
        continue;
      }

      console.log("✅ Got:", data.userProfile.fullName);
      results.push(data);

      const waitTime = 10000 + Math.random() * 10000;
      console.log(`⏳ Waiting ${Math.floor(waitTime / 1000)} sec...\n`);
      await delay(waitTime);

    } catch (err) {
      console.log("❌ Error:", err.message);
    }
  }

  fs.writeFileSync("linkedin_results.json", JSON.stringify(results, null, 2));

  console.log("\n🎉 Done!");
})();