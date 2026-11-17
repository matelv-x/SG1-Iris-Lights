/* Bridge SG1 Iris browser state to the optional physical LED indicator. */
const stateUrl = '/stargate/get/iris_lights';
const updateUrl = '/stargate/update/iris_lights';

async function sendState(closed) {
  try {
    const response = await fetch(updateUrl, {
      method: 'POST',
      cache: 'no-store',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({closed}),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
  } catch (error) {
    console.warn('[sg1-iris-lights] Could not synchronize physical LEDs', error);
  }
}

document.addEventListener('iris:state', event => {
  if (typeof event.detail?.closed === 'boolean') sendState(event.detail.closed);
});

async function restoreState() {
  try {
    const response = await fetch(stateUrl, {cache: 'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const state = await response.json();
    if (state.closed && window.sg1Iris && !window.sg1Iris.isClosed()) {
      window.sg1Iris.close();
    }
  } catch (error) {
    console.warn('[sg1-iris-lights] Could not read physical LED state', error);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', restoreState, {once: true});
} else {
  restoreState();
}
