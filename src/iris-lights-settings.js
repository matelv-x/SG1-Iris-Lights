(() => {
  const enabled = document.getElementById('iris-lights-enabled');
  const closed = document.getElementById('iris-lights-closed');
  const autoIncoming = document.getElementById('iris-lights-auto-incoming');
  const autoOpen = document.getElementById('iris-lights-auto-open');
  const interval = document.getElementById('iris-lights-interval');
  const offset = document.getElementById('iris-lights-offset');
  const positions = document.getElementById('iris-lights-positions');
  const save = document.getElementById('iris-lights-save');
  const message = document.getElementById('iris-lights-message');
  if (!enabled || !closed || !autoIncoming || !autoOpen || !interval
      || !offset || !positions || !save || !message) return;

  async function request(path, options) {
    const response = await fetch('/stargate' + path, options);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const payload = await response.json();
    if (payload.success === false) throw new Error(payload.message || 'Update failed');
    return payload;
  }

  function showPositions(state) {
    positions.textContent = Array.isArray(state.indices)
      ? 'LED positions: ' + state.indices.join(', ')
      : '';
  }

  async function load() {
    try {
      const state = await request('/get/iris_lights');
      enabled.checked = state.enabled === true;
      closed.checked = state.closed === true;
      autoIncoming.checked = state.auto_incoming === true;
      autoOpen.value = state.auto_open_seconds;
      interval.value = state.flash_interval_seconds;
      offset.value = state.offset;
      offset.max = Math.max(0, Number(state.led_count) - 1);
      showPositions(state);
      message.textContent = '';
    } catch (error) {
      message.textContent = 'Could not load Iris Lights settings: ' + error.message;
    }
  }

  save.addEventListener('click', async () => {
    const seconds = Number(interval.value);
    const offsetValue = Number(offset.value);
    const autoOpenSeconds = Number(autoOpen.value);
    const maximum = Number(offset.max);
    if (!Number.isInteger(seconds) || seconds < 1 || seconds > 3600) {
      message.textContent = 'Enter a whole interval from 1 to 3600 seconds.';
      return;
    }
    if (!Number.isInteger(offsetValue) || offsetValue < 0 || offsetValue > maximum) {
      message.textContent = `Enter an LED offset from 0 to ${maximum}.`;
      return;
    }
    if (!Number.isInteger(autoOpenSeconds) || autoOpenSeconds < 0 || autoOpenSeconds > 3600) {
      message.textContent = 'Enter an automatic open time from 0 to 3600 seconds.';
      return;
    }
    save.disabled = true;
    message.textContent = 'Saving…';
    try {
      const state = await request('/update/iris_lights_preferences', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          enabled: enabled.checked,
          flash_interval_seconds: seconds,
          offset: offsetValue,
          auto_incoming: autoIncoming.checked,
          auto_open_seconds: autoOpenSeconds,
        }),
      });
      const closedState = await request('/update/iris_lights', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({closed: closed.checked}),
      });
      closed.checked = closedState.closed === true;
      showPositions(closedState);
      message.textContent = 'Saved. Changes take effect immediately.';
    } catch (error) {
      message.textContent = 'Could not save Iris Lights settings: ' + error.message;
    } finally {
      save.disabled = false;
    }
  });

  load();
})();
