require("dotenv").config();
const puppeteer = require("puppeteer");

(async () => {
  if (!process.env.LI_AT) {
    throw new Error("❌ Missing LI_AT cookie");
  }

  console.log("🚀 Launching browser...");

  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null
  });

  const page = await browser.newPage();

  // 🔹 Step 1: Go to LinkedIn FIRST (important)
  await page.goto("https://www.linkedin.com", {
    waitUntil: "domcontentloaded"
  });

  // 🔹 Step 2: Set cookie
  await page.setCookie({
    name: "li_at",
    value: process.env.LI_AT,
    domain: ".linkedin.com",
    path: "/",
    httpOnly: true,
    secure: true
  });

  // 🔹 Step 3: Reload to apply cookie
  await page.reload({ waitUntil: "networkidle2" });

  // 🔹 Step 4: Check login properly
  const currentUrl = page.url();

  if (currentUrl.includes("login") || currentUrl.includes("authwall")) {
    console.log("❌ Cookie invalid / session rejected");
    await browser.close();
    return;
  }

  console.log("✅ Logged in successfully!");

  // 🔹 Step 5: Open profile
  const profileUrl = "https://www.linkedin.com/in/ananddubey104/";
  console.log("🔍 Opening profile...");

  await page.goto(profileUrl, { waitUntil: "networkidle2" });

  // 🔹 Step 6: Wait for page to fully load
  await page.waitForSelector("h1", { timeout: 10000 });

  // 🔹 Step 7: Extract name
  const name = await page.evaluate(() => {
    const el = document.querySelector("h1");
    return el ? el.innerText : null;
  });

  console.log("👤 Name:", name);

  console.log("🎉 Done!");
})();