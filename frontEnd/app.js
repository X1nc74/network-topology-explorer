import { renderGraph } from "./graph.js";
import { transformRawResults } from "./data.js";

const DATA_PATH = "../output/results.json";

async function bootstrap() {
  try {
    const response = await fetch(DATA_PATH, { cache: "no-store" });
    if (!response.ok) throw new Error("Generate output/results.json before opening the explorer.");
    renderGraph(transformRawResults(await response.json()));
  } catch (error) {
    console.error(error);
    const panel = document.createElement("div");
    panel.style.cssText = "padding:24px;font-family:sans-serif";
    const heading = document.createElement("h2");
    heading.textContent = "Failed to load data";
    const message = document.createElement("p");
    message.textContent = error.message;
    const help = document.createElement("p");
    help.textContent = "Run a trace first, then serve the project root with a local HTTP server.";
    panel.append(heading, message, help);
    document.body.replaceChildren(panel);
  }
}

bootstrap();
