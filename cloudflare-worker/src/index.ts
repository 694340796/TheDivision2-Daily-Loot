interface ScheduledController {
  cron: string;
  scheduledTime: number;
}

export interface Env {
  GITHUB_TOKEN: string;
  GITHUB_OWNER?: string;
  GITHUB_REPO?: string;
  GITHUB_REF?: string;
}

const FETCH_CRON = "1 8 * * *"; // Beijing 16:01
const PUSH_CRON = "2 8 * * *";  // Beijing 16:02
const GITHUB_API_VERSION = "2022-11-28";

async function dispatchWorkflow(
  env: Env,
  workflowFile: string,
  inputs?: Record<string, string | boolean>,
): Promise<void> {
  const owner = env.GITHUB_OWNER || "694340796";
  const repo = env.GITHUB_REPO || "TheDivision2-Daily-Loot";
  const ref = env.GITHUB_REF || "main";
  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowFile}/dispatches`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "X-GitHub-Api-Version": GITHUB_API_VERSION,
      "Content-Type": "application/json",
      "User-Agent": "thedivision2-daily-loot-cloudflare-worker",
    },
    body: JSON.stringify({ ref, ...(inputs ? { inputs } : {}) }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `GitHub workflow dispatch failed (${response.status}) for ${workflowFile}: ${detail}`,
    );
  }

  console.log(
    JSON.stringify({
      event: "workflow_dispatched",
      workflow: workflowFile,
      ref,
      scheduledAt: new Date().toISOString(),
      status: response.status,
    }),
  );
}

export default {
  async scheduled(
    controller: ScheduledController,
    env: Env,
    _ctx: unknown,
  ): Promise<void> {
    if (!env.GITHUB_TOKEN) {
      throw new Error("Missing Cloudflare Worker secret: GITHUB_TOKEN");
    }

    console.log(
      JSON.stringify({
        event: "cron_started",
        cron: controller.cron,
        scheduledTime: new Date(controller.scheduledTime).toISOString(),
      }),
    );

    if (controller.cron === FETCH_CRON) {
      await dispatchWorkflow(env, "daily-loot-fetch.yml");
      return;
    }

    if (controller.cron === PUSH_CRON) {
      // Include a small lead-in window so the 16:01 Fetch dispatch is found
      // even if Cloudflare invokes this scheduled event a little late/early.
      const fetchNotBefore = new Date(
        controller.scheduledTime - 3 * 60 * 1000,
      ).toISOString();

      await dispatchWorkflow(env, "daily-loot-push.yml", {
        wait_for_fetch: "true",
        fetch_not_before: fetchNotBefore,
      });
      return;
    }

    console.log(
      JSON.stringify({
        event: "ignored_cron",
        cron: controller.cron,
      }),
    );
  },

  async fetch(request: Request): Promise<Response> {
    if (request.method !== "GET") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    return Response.json({
      ok: true,
      service: "TheDivision2 Daily Loot GitHub Actions Scheduler",
      schedules: {
        fetch: "Every day at 16:01 Asia/Shanghai (08:01 UTC)",
        push: "Every day at 16:02 Asia/Shanghai (08:02 UTC)",
      },
      note: "This endpoint is a health check. Cron triggers perform the dispatch.",
    });
  },
};
