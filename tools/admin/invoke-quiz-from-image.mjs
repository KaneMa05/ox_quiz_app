/**
 * 관리자 전용: OX_QUIZ_ADMIN_TOOLS 를 설정한 뒤 Python 가공 스크립트를 실행합니다.
 * 퀴즈 웹앱(index.html 등)과 무관한 별도 진입점입니다.
 *
 * image_to_quiz_questions.py 를 실행합니다.
 *   무료 OCR: … --ocr page.jpg   (Tesseract + kor, OpenAI 없음)
 *   Vision: … page.jpg   (OPENAI_API_KEY — .env.local / api.env.local)
 *   예: node tools/admin/invoke-quiz-from-image.mjs --ocr page.jpg --pack-no 301 --sql
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const script = path.join(__dirname, "image_to_quiz_questions.py");
const forwarded = process.argv.slice(2);

process.env.OX_QUIZ_ADMIN_TOOLS = "1";

function trySpawn(cmd, args) {
  return spawnSync(cmd, args, { stdio: "inherit", env: process.env });
}

let r = trySpawn("py", ["-3", script, ...forwarded]);
if (r.error?.code === "ENOENT") {
  r = trySpawn("python3", [script, ...forwarded]);
}
if (r.error?.code === "ENOENT") {
  r = trySpawn("python", [script, ...forwarded]);
}
if (r.error) {
  console.error(r.error.message);
  process.exit(127);
}
process.exit(r.status ?? 1);
