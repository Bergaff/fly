#!/usr/bin/env node
/**
 * fly-mcp: MCP-сервер к приложению Fly Ideas.
 *
 * Работает по stdio (JSON-RPC построчно), не требует ничего кроме Node.
 * Все чтения, записи и запуски идут через локальный мост самого приложения
 * (127.0.0.1, токен из agent.json), поэтому приложение остаётся источником правды:
 * оно проверяет права, пишет журнал, копит прогоны и показывает уведомления.
 *
 * Подключение в DeepSeek Harness (dsh) или любом MCP-хосте:
 *   команда: node
 *   аргументы: <путь к этому файлу>
 *
 * Где искать agent.json (по порядку):
 *   1) переменная окружения FLY_IDEAS_USER_DATA
 *   2) аргумент --user-data <папка>
 *   3) системные пути: %APPDATA%/fly-ideas, ~/Library/Application Support/fly-ideas, ~/.config/fly-ideas
 *
 * Если приложение не запущено, инструменты вернут подсказку открыть Fly Ideas.
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const APP_NAME = "fly-ideas";
const PROTOCOL_FALLBACK = "2025-06-18";

function userDataCandidates() {
  const out = [];
  const fromEnv = process.env.FLY_IDEAS_USER_DATA;
  if (fromEnv) out.push(fromEnv);
  const argIdx = process.argv.indexOf("--user-data");
  if (argIdx > -1 && process.argv[argIdx + 1]) out.push(process.argv[argIdx + 1]);
  if (process.platform === "win32") out.push(path.join(process.env.APPDATA || "", APP_NAME));
  else if (process.platform === "darwin") out.push(path.join(os.homedir(), "Library", "Application Support", APP_NAME));
  else out.push(path.join(os.homedir(), ".config", APP_NAME));
  return out.filter(Boolean);
}

function readAgent() {
  const tried = [];
  for (const dir of userDataCandidates()) {
    const file = path.join(dir, "agent.json");
    tried.push(file);
    try {
      const j = JSON.parse(fs.readFileSync(file, "utf8"));
      if (j && j.port && j.token) return { ...j, file };
    } catch {
      /* пробуем следующий путь */
    }
  }
  throw new Error(
    "Не нашёл agent.json. Запусти приложение Fly Ideas (START.bat) и включи «Подключение агента» во вкладке Мозг, раздел «Данные и окружение». Искал: " +
      tried.join(", "),
  );
}

async function callApi(route, { method = "GET", body, query } = {}) {
  const agent = readAgent();
  const url = new URL(`http://127.0.0.1:${agent.port}/api${route}`);
  for (const [k, v] of Object.entries(query || {})) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${agent.token}` },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(`Приложение Fly Ideas не отвечает на порту ${agent.port}. Открой его (START.bat) и повтори.`);
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text.slice(0, 2000) };
  }
  if (!res.ok) throw new Error(data && data.error ? data.error : `HTTP ${res.status}`);
  return data;
}

const TOOLS = [
  {
    name: "fly_status",
    description:
      "Состояние приложения Fly Ideas: проекты, число идей и источников, права на файлы, папки кода, прогонов и данных, путь к agent.json. Вызови первым, чтобы понять обстановку.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    run: () => callApi("/status"),
  },
  {
    name: "fly_list_projects",
    description: "Список проектов: id, название, описание, сколько идей в каждом.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    run: () => callApi("/projects"),
  },
  {
    name: "fly_list_ideas",
    description: "Идеи проекта или всех проектов. Кратко: id, название, статус, оценки, прогресс чеклиста, дедлайн, метки.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string", description: "id проекта или all (по умолчанию all)" },
        status: { type: "string", description: "backlog | exploring | active | drafting | submitted | done | parked" },
        query: { type: "string", description: "подстрока в названии, вопросе или метках" },
        limit: { type: "number", description: "сколько вернуть, по умолчанию 40" },
      },
      additionalProperties: false,
    },
    run: (a) => callApi("/ideas", { query: a }),
  },
  {
    name: "fly_get_idea",
    description: "Полная карточка идеи: вопрос, метод, валидация, заметки, оценки, чеклист с датами, журнал прогонов, источники с пометкой «зачем», связи с другими идеями.",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string", description: "id идеи" },
        title: { type: "string", description: "или часть названия, если id неизвестен" },
      },
      additionalProperties: false,
    },
    run: (a) => callApi("/idea", { query: a }),
  },
  {
    name: "fly_search_library",
    description: "Поиск по общей библиотеке источников: автор, год, название, журнал, DOI, теги, конспект. Полезно перед тем, как предлагать литературу.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "подстрока: автор, название, DOI, тег" },
        tag: { type: "string" },
        limit: { type: "number" },
      },
      additionalProperties: false,
    },
    run: (a) => callApi("/library", { query: a }),
  },
  {
    name: "fly_list_scripts",
    description: "Файлы .py в папке кода проекта: имя, размер, время изменения, первая строка-описание. Прогоны запускаются только из этой папки.",
    inputSchema: {
      type: "object",
      properties: { projectId: { type: "string", description: "id проекта" } },
      required: ["projectId"],
      additionalProperties: false,
    },
    run: (a) => callApi("/scripts", { query: a }),
  },
  {
    name: "fly_read_script",
    description: "Прочитать исходник скрипта проекта целиком.",
    inputSchema: {
      type: "object",
      properties: { projectId: { type: "string" }, name: { type: "string", description: "имя файла, например 06_brian2_shiu.py" } },
      required: ["projectId", "name"],
      additionalProperties: false,
    },
    run: (a) => callApi("/script", { query: a }),
  },
  {
    name: "fly_list_runs",
    description: "Недавние прогоны проекта: папка, время, файлы, краткая сводка summary.json.",
    inputSchema: {
      type: "object",
      properties: { projectId: { type: "string" }, limit: { type: "number", description: "по умолчанию 20" } },
      required: ["projectId"],
      additionalProperties: false,
    },
    run: (a) => callApi("/runs", { query: { ...a, limit: a.limit ?? 20 } }),
  },
  {
    name: "fly_read_run",
    description: "Итог конкретного прогона: summary.json, список файлов, хвост log.txt. Числа из summary лучше не пересказывать словами, а приводить как есть.",
    inputSchema: {
      type: "object",
      properties: { dir: { type: "string", description: "полный путь к папке прогона из fly_list_runs" } },
      required: ["dir"],
      additionalProperties: false,
    },
    run: (a) => callApi("/run", { query: a }),
  },
  {
    name: "fly_list_data",
    description: "Что уже скачано в папку данных: коннектом FlyWire v783, таблицы MaleCNS, скелеты, размеры. Перед запуском моделей проверяй здесь.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    run: () => callApi("/data"),
  },
  {
    name: "fly_run_script",
    description:
      "Запустить прогон скрипта проекта. Скрипт получает FLY_DATA, FLY_RUN_DIR, FLY_SCRIPTS. Возвращает runId и папку прогона; узнать итог можно через fly_wait_run или fly_read_run. Сначала убедись, что окружение готово (fly_status, fly_list_data), и что скрипт читает данные проекта, а не чужие пути.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        script: { type: "string", description: "имя .py из fly_list_scripts" },
        args: { type: "array", items: { type: "string" }, description: "аргументы, каждый отдельной строкой, например [\"--synth\",\"--n\",\"800\"]" },
      },
      required: ["projectId", "script"],
      additionalProperties: false,
    },
    run: (a) => callApi("/run", { method: "POST", body: { projectId: a.projectId, script: a.script, args: a.args || [] } }),
  },
  {
    name: "fly_wait_run",
    description: "Дождаться конца прогона и вернуть summary и хвост лога. Используй после fly_run_script, чтобы не гадать, чем кончилось.",
    inputSchema: {
      type: "object",
      properties: {
        runId: { type: "string" },
        timeoutSec: { type: "number", description: "сколько ждать, по умолчанию 120, максимум 600" },
      },
      required: ["runId"],
      additionalProperties: false,
    },
    run: async (a) => {
      const cap = Math.min(Math.max(a.timeoutSec ?? 120, 5), 600);
      const started = Date.now();
      for (;;) {
        const st = await callApi("/run/status", { query: { runId: a.runId } });
        if (!st.running) {
          const full = await callApi("/run", { query: { dir: st.dir } });
          return { ...st, ...full };
        }
        if ((Date.now() - started) / 1000 > cap) return { ...st, timeout: true, note: "прогон ещё идёт, проверь позже через fly_read_run" };
        await new Promise((r) => setTimeout(r, 2000));
      }
    },
  },
  {
    name: "fly_kill_run",
    description: "Остановить прогон.",
    inputSchema: { type: "object", properties: { runId: { type: "string" } }, required: ["runId"], additionalProperties: false },
    run: (a) => callApi("/kill", { method: "POST", body: { runId: a.runId } }),
  },
  {
    name: "fly_add_journal_entry",
    description:
      "Добавить запись в лабораторный журнал идеи. Пиши конкретно: что запускал, параметры, сид, что получилось числами, вывод. Запись сразу видна в приложении.",
    inputSchema: {
      type: "object",
      properties: {
        ideaId: { type: "string" },
        title: { type: "string", description: "что запускал" },
        params: { type: "string", description: "параметры, сид, бэкенд, коммит" },
        result: { type: "string", description: "что получилось, по возможности с числами" },
        conclusion: { type: "string", description: "вывод и что дальше" },
        outcome: { type: "string", description: "success | partial | failed | inconclusive" },
      },
      required: ["ideaId", "title"],
      additionalProperties: false,
    },
    run: (a) => callApi("/journal", { method: "POST", body: a }),
  },
  {
    name: "fly_add_idea",
    description: "Завести новую идею в проекте. Возвращает id, дальше её можно дополнять через fly_update_idea.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string", description: "id проекта, по умолчанию первый" },
        title: { type: "string" },
        question: { type: "string", description: "исследовательский вопрос" },
        method: { type: "string", description: "как проверяем" },
        validation: { type: "string", description: "с чем сверяем" },
      },
      required: ["title"],
      additionalProperties: false,
    },
    run: (a) => callApi("/idea", { method: "POST", body: a }),
  },
  {
    name: "fly_update_idea",
    description:
      "Правка идеи: статус, вопрос, метод, валидация, заметки, сроки, метки, оценки, журналы для подачи. Передавай только те поля, которые меняются.",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string" },
        status: { type: "string" },
        question: { type: "string" },
        method: { type: "string" },
        validation: { type: "string" },
        notes: { type: "string" },
        deadline: { type: "string", description: "YYYY-MM-DD или пусто" },
        tags: { type: "array", items: { type: "string" } },
        scores: {
          type: "object",
          description: "оценки 1-10",
          properties: {
            effort: { type: "number" },
            impact: { type: "number" },
            novelty: { type: "number" },
            speed: { type: "number" },
            risk: { type: "number" },
          },
        },
      },
      required: ["id"],
      additionalProperties: false,
    },
    run: (a) => {
      const { id, ...patch } = a;
      return callApi("/idea/patch", { method: "POST", body: { id, patch } });
    },
  },
  {
    name: "fly_add_reference",
    description: "Добавить источник в общую библиотеку. Если есть DOI, он разберётся в ссылку.",
    inputSchema: {
      type: "object",
      properties: {
        authors: { type: "string" },
        year: { type: "number" },
        title: { type: "string" },
        venue: { type: "string", description: "журнал или препринт" },
        doi: { type: "string" },
        url: { type: "string" },
        notes: { type: "string", description: "конспект: что оттуда берём" },
        tags: { type: "array", items: { type: "string" } },
      },
      required: ["title"],
      additionalProperties: false,
    },
    run: (a) => callApi("/reference", { method: "POST", body: a }),
  },
];

const BY_NAME = new Map(TOOLS.map((t) => [t.name, t]));

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + "\n");
}
const ok = (id, result) => send({ jsonrpc: "2.0", id, result });
const fail = (id, code, message) => send({ jsonrpc: "2.0", id, error: { code, message } });

async function handle(msg) {
  const { id, method, params } = msg;
  if (method === "initialize") {
    ok(id, {
      protocolVersion: params?.protocolVersion || PROTOCOL_FALLBACK,
      capabilities: { tools: { listChanged: false } },
      serverInfo: { name: "fly-ideas", version: "1.0.0" },
      instructions:
        "Инструменты приложения Fly Ideas: идеи, журнал прогонов, библиотека, данные коннектома и запуск python-скриптов проекта. " +
        "Начинай с fly_status, чтобы увидеть проекты, права и папки.",
    });
    return;
  }
  if (method === "notifications/initialized" || method === "notifications/cancelled") return;
  if (method === "ping") {
    ok(id, {});
    return;
  }
  if (method === "tools/list") {
    ok(id, { tools: TOOLS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })) });
    return;
  }
  if (method === "tools/call") {
    const tool = BY_NAME.get(params?.name);
    if (!tool) {
      ok(id, { content: [{ type: "text", text: `Нет инструмента ${params?.name}` }], isError: true });
      return;
    }
    try {
      const result = await tool.run(params?.arguments || {});
      ok(id, { content: [{ type: "text", text: JSON.stringify(result, null, 1) }] });
    } catch (e) {
      ok(id, { content: [{ type: "text", text: `Ошибка: ${e.message}` }], isError: true });
    }
    return;
  }
  if (method === "resources/list") {
    ok(id, { resources: [] });
    return;
  }
  if (method === "prompts/list") {
    ok(id, { prompts: [] });
    return;
  }
  if (id !== undefined) fail(id, -32601, `Метод не поддержан: ${method}`);
}

let buffer = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", async (chunk) => {
  buffer += chunk;
  let idx;
  while ((idx = buffer.indexOf("\n")) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      continue;
    }
    try {
      await handle(msg);
    } catch (e) {
      if (msg && msg.id !== undefined) fail(msg.id, -32603, e.message);
    }
  }
});
process.stdin.on("end", () => process.exit(0));
