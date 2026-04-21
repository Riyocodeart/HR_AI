const fs = require("fs");
const { LinkedInProfileScraper } = require("linkedin-profile-scraper");

const delay = (ms) => new Promise((res) => setTimeout(res, ms));

(async () => {
  const scraper = new LinkedInProfileScraper({
    sessionCookieValue: "AQEDAWIvuk8E1w5MAAABna2xtXsAAAGd0b45e04ADNtYwY248lMbKU8__bUfOhw8d19Rqhzqs0b2OSkD0-Wc6DZptMebdm3JLG-1fYlD5WasxKvxua7fvyxJxYsTW3vY160o7RZ3q3Y6cmqt-yZroj7t",
    keepAlive: true
  });

  console.log("🚀 Starting scraper...");
  await scraper.setup();

  const profileUrls = [
    "https://www.linkedin.com/in/ananddubey104/",
    "https://www.linkedin.com/in/anujhsawant/",
    "https://www.linkedin.com/in/atharva2706/"
  ];

  let results = [];

  for (let i = 0; i < profileUrls.length; i++) {
    const url = profileUrls[i];

    try {
      console.log(`\n🔍 Scraping (${i + 1}/${profileUrls.length}): ${url}`);

      const data = await scraper.run(url);
      results.push(data);

      console.log("✅ Done");

      const waitTime = 5000 + Math.random() * 3000;
      console.log(`⏳ Waiting ${Math.floor(waitTime / 1000)} sec...\n`);
      await delay(waitTime);

    } catch (err) {
      console.log("❌ Error scraping:", url);
      console.log(err.message);
    }
  }

  fs.writeFileSync("linkedin_results.json", JSON.stringify(results, null, 2));

  console.log("\n🎉 Scraping completed!");
})();