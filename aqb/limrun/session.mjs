// Hold one Limrun Android instance and its adb tunnel for the Android QA benchmark.
//
//   LIM_API_KEY=... node session.mjs [--hard-timeout 4h] [--inactivity 15m] [--region us]
//
// Prints one JSON line to stdout once ready:
//   {"event":"ready","serial":"127.0.0.1:PORT","id":"...","region":"..."}
// then keeps the tunnel open until stdin closes or SIGINT/SIGTERM, and always
// deletes the instance on exit. hardTimeout is a backstop so a forgotten
// instance cannot run (and bill) indefinitely.
import { Limrun, createInstanceClient } from '@limrun/api';

const args = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
};

const emit = (obj) => process.stdout.write(JSON.stringify(obj) + '\n');
const log = (msg) => process.stderr.write(`[limrun] ${msg}\n`);

if (!process.env.LIM_API_KEY) {
  emit({ event: 'error', message: 'LIM_API_KEY is not set' });
  process.exit(2);
}

const client = new Limrun();
let instanceId = null;
let tunnel = null;
let closing = false;

async function shutdown(code = 0) {
  if (closing) return;
  closing = true;
  try { tunnel?.close(); } catch {}
  if (instanceId) {
    try {
      await client.androidInstances.delete(instanceId);
      log(`deleted instance ${instanceId}`);
    } catch (e) {
      log(`delete failed for ${instanceId}: ${e?.message ?? e} (hardTimeout will reap it)`);
    }
  }
  emit({ event: 'closed', id: instanceId });
  process.exit(code);
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));
process.stdin.on('end', () => shutdown(0));
process.stdin.resume();

try {
  const spec = {
    model: 'phone',
    inactivityTimeout: opt('--inactivity', '15m'),
    hardTimeout: opt('--hard-timeout', '4h'),
  };
  const region = opt('--region', null);
  if (region) spec.region = region;
  log('creating instance (wait for ready)...');
  const inst = await client.androidInstances.create({
    wait: true,
    metadata: { displayName: 'aqb-calibration', labels: { purpose: 'aqb' } },
    spec,
  });
  instanceId = inst.metadata.id;
  const st = inst.status;
  if (st.state !== 'ready' || !st.adbWebSocketUrl || !st.token) {
    emit({ event: 'error', message: `instance not ready: ${st.state} ${st.errorMessage ?? ''}`, id: instanceId });
    await shutdown(3);
  }
  const ic = await createInstanceClient({ apiUrl: st.apiUrl, adbUrl: st.adbWebSocketUrl, token: st.token, logLevel: 'warn' });
  tunnel = await ic.startAdbTunnel();
  const serial = `${tunnel.address.address}:${tunnel.address.port}`;
  emit({ event: 'ready', serial, id: instanceId, region: inst.spec?.region ?? null });
} catch (e) {
  emit({ event: 'error', message: String(e?.message ?? e), id: instanceId });
  await shutdown(1);
}
