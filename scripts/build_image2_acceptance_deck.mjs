import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) out[argv[i].replace(/^--/, "")] = argv[i + 1];
  if (!out.input || !out.output) throw new Error("--input and --output are required");
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const input = path.resolve(options.input);
  const output = path.resolve(options.output);
  const names = (await fs.readdir(input)).filter((name) => /^\d{2}-.+\.png$/i.test(name)).sort();
  if (!names.length) throw new Error(`No generated slide images found in ${input}`);
  const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  const master = deck.masters.add("image2--brand-editorial");
  const layout = deck.layouts.add("layout--full-bleed-image");
  layout.setParentLayoutId(master.id);
  for (const name of names) {
    const slide = deck.slides.add();
    slide.setLayout(layout);
    const data = await fs.readFile(path.join(input, name));
    const dataUrl = `data:image/png;base64,${data.toString("base64")}`;
    const image = slide.images.add({ dataUrl, fit: "fill", alt: name, name });
    image.position = { left: 0, top: 0, width: 1280, height: 720 };
  }
  await fs.mkdir(path.dirname(output), { recursive: true });
  const file = await PresentationFile.exportPptx(deck);
  await file.save(output);
  console.log(JSON.stringify({ slides: names.length, output }));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
