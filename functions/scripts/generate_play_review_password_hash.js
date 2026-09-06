/**
 * Generates the value for the PLAY_REVIEW_PASSWORD_SCRYPT secret without
 * printing the password. Run from functions/: node scripts/generate_play_review_password_hash.js
 */
const { randomBytes, scryptSync } = require("crypto");
const readline = require("readline");

if (!process.stdin.isTTY) {
  console.error("Run this script in an interactive terminal.");
  process.exit(2);
}

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
process.stdout.write("Review password (24+ characters): ");
process.stdin.setRawMode(true);
let password = "";

process.stdin.on("data", (buffer) => {
  const text = buffer.toString("utf8");
  if (text === "\u0003") process.exit(130);
  if (text === "\r" || text === "\n") {
    process.stdin.setRawMode(false);
    process.stdout.write("\n");
    rl.close();
    if (password.length < 24) {
      console.error("Password must contain at least 24 characters.");
      process.exit(2);
    }
    const salt = randomBytes(16);
    const key = scryptSync(password, salt, 32, {
      N: 16384,
      r: 8,
      p: 1,
      maxmem: 64 * 1024 * 1024,
    });
    password = "";
    process.stdout.write(
      `scrypt-v1:${salt.toString("base64")}:${key.toString("base64")}\n`,
    );
    return;
  }
  if (text === "\u007f") {
    password = password.slice(0, -1);
    return;
  }
  password += text;
});
