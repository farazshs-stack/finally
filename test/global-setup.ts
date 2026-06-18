import fs from "fs";
import path from "path";

export default async function globalSetup() {
  // The DB is already created by the webServer at this point.
  // We pre-delete it from start-server.sh before uvicorn starts.
  // Just ensure the .tmp directory exists.
  fs.mkdirSync(path.join(__dirname, ".tmp"), { recursive: true });
  console.log("[globalSetup] .tmp directory confirmed");
}
