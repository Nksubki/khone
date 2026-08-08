/* =========================================================================
   KhoneVoice — ورودی صوتی فارسی با Web Speech API
   دو حالت:
     mode="amount" → گفته را به عدد تبدیل می‌کند («صد و بیست میلیون»)
     mode="text"   → متن گفته‌شده را در فیلد می‌نویسد
   ========================================================================= */
(function (global) {
  'use strict';

  var Recognition = global.SpeechRecognition || global.webkitSpeechRecognition;

  var overlay, titleEl, transcriptEl, parsedEl, acceptBtn, cancelBtn;
  var state = {
    active: false,
    mode: 'text',
    input: null,
    button: null,
    previousValue: '',
    lastTranscript: '',
    recognition: null,
    applied: false
  };

  function isSupported() { return !!Recognition; }

  function grabElements() {
    overlay = document.getElementById('voice-overlay');
    titleEl = document.getElementById('voice-title');
    transcriptEl = document.getElementById('voice-transcript');
    parsedEl = document.getElementById('voice-parsed');
    acceptBtn = document.getElementById('voice-accept');
    cancelBtn = document.getElementById('voice-cancel');
  }

  function showOverlay(mode) {
    if (!overlay) { return; }
    overlay.hidden = false;
    if (titleEl) {
      titleEl.textContent = mode === 'amount'
        ? 'مبلغ را بگویید…'
        : 'بفرمایید، در حال شنیدن…';
    }
    if (transcriptEl) { transcriptEl.textContent = 'گوش می‌دهم…'; }
    if (parsedEl) { parsedEl.textContent = ''; }
    if (acceptBtn) { acceptBtn.textContent = 'تأیید'; }
    if (cancelBtn) { cancelBtn.textContent = 'لغو'; }
  }

  function hideOverlay() {
    if (overlay) { overlay.hidden = true; }
  }

  function setButtonRecording(on) {
    if (!state.button) { return; }
    state.button.classList.toggle('recording', !!on);
  }

  function markVoiceUsed() {
    var flag = document.getElementById('voice-used');
    if (flag) { flag.value = '1'; }
  }

  function applyResult(transcript) {
    if (!state.input) { return; }
    var text = (transcript || '').trim();
    if (!text) { return; }

    if (state.mode === 'amount') {
      var value = global.KhoneNumber ? global.KhoneNumber.parse(text) : null;
      if (value === null) {
        if (parsedEl) { parsedEl.textContent = 'عدد تشخیص داده نشد؛ دوباره بگویید یا دستی بنویسید.'; }
        return;
      }
      state.input.value = global.KhoneNumber.format(value, false);
      state.input.dispatchEvent(new Event('input', { bubbles: true }));
      if (parsedEl) {
        parsedEl.textContent = global.KhoneNumber.format(value, true) + ' تومان  ('
          + global.KhoneNumber.toWords(value) + ')';
      }
    } else {
      var normalized = global.KhoneNumber ? global.KhoneNumber.normalize(text) : text;
      var existing = (state.previousValue || '').trim();
      state.input.value = existing ? (existing + ' ' + normalized) : normalized;
      state.input.dispatchEvent(new Event('input', { bubbles: true }));
      if (parsedEl) { parsedEl.textContent = 'در فیلد نوشته شد ✓'; }
    }
    state.applied = true;
    markVoiceUsed();
  }

  function stopRecognition() {
    if (state.recognition) {
      try { state.recognition.onend = null; state.recognition.stop(); } catch (e) {}
    }
    state.recognition = null;
    state.active = false;
    setButtonRecording(false);
  }

  function finish() {
    stopRecognition();
    hideOverlay();
    state.input = null;
    state.button = null;
  }

  function revert() {
    if (state.applied && state.input) {
      state.input.value = state.previousValue;
      state.input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    finish();
  }

  function pickBestAlternative(result) {
    // بین چند حدس، حدسی را انتخاب می‌کند که به عدد قابل تبدیل باشد
    var best = result[0] ? result[0].transcript : '';
    if (state.mode !== 'amount' || !global.KhoneNumber) { return best; }
    for (var i = 0; i < result.length; i++) {
      var text = result[i].transcript;
      if (global.KhoneNumber.parse(text) !== null) { return text; }
    }
    return best;
  }

  function start(button) {
    if (!isSupported()) {
      alert('مرورگر شما از ورودی صوتی پشتیبانی نمی‌کند.\nپیشنهاد: کروم روی اندروید/ویندوز یا سافاری روی آیفون.');
      return;
    }
    grabElements();

    var selector = button.getAttribute('data-target');
    var input = selector ? document.querySelector(selector) : null;
    if (!input) { return; }

    if (state.active) { stopRecognition(); }

    state.mode = button.getAttribute('data-voice') === 'amount' ? 'amount' : 'text';
    state.input = input;
    state.button = button;
    state.previousValue = input.value || '';
    state.lastTranscript = '';
    state.applied = false;

    var recognition = new Recognition();
    recognition.lang = 'fa-IR';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 5;

    recognition.onstart = function () {
      state.active = true;
      setButtonRecording(true);
      showOverlay(state.mode);
    };

    recognition.onresult = function (event) {
      var interim = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var result = event.results[i];
        if (result.isFinal) {
          var text = pickBestAlternative(result);
          state.lastTranscript = text;
          if (transcriptEl) { transcriptEl.textContent = text; }
          applyResult(text);
        } else {
          interim += result[0].transcript;
        }
      }
      if (interim && transcriptEl) {
        transcriptEl.textContent = interim;
        if (state.mode === 'amount' && parsedEl && global.KhoneNumber) {
          var guess = global.KhoneNumber.parse(interim);
          parsedEl.textContent = guess === null ? '' : global.KhoneNumber.format(guess, true) + ' تومان';
        }
      }
    };

    recognition.onerror = function (event) {
      var messages = {
        'not-allowed': 'دسترسی به میکروفون داده نشده است. از تنظیمات مرورگر اجازه دهید.',
        'service-not-allowed': 'سرویس تشخیص گفتار در دسترس نیست.',
        'no-speech': 'صدایی شنیده نشد؛ دوباره تلاش کنید.',
        'audio-capture': 'میکروفون پیدا نشد.',
        'network': 'برای تشخیص گفتار به اینترنت نیاز است.'
      };
      if (transcriptEl) {
        transcriptEl.textContent = messages[event.error] || ('خطا: ' + event.error);
      }
      setButtonRecording(false);
      state.active = false;
    };

    recognition.onend = function () {
      state.active = false;
      setButtonRecording(false);
      if (overlay && !overlay.hidden) {
        if (acceptBtn) { acceptBtn.textContent = state.applied ? 'تمام' : 'بستن'; }
        if (cancelBtn) { cancelBtn.textContent = 'تکرار'; }
        if (transcriptEl && !state.lastTranscript) {
          transcriptEl.textContent = 'چیزی شنیده نشد؛ دکمه «تکرار» را بزنید.';
        }
      }
    };

    state.recognition = recognition;
    try {
      recognition.start();
    } catch (e) {
      showOverlay(state.mode);
      if (transcriptEl) { transcriptEl.textContent = 'شروع ضبط ممکن نشد؛ دوباره تلاش کنید.'; }
    }
  }

  function retry() {
    var button = state.button;
    if (state.applied && state.input) {
      state.input.value = state.previousValue;
      state.input.dispatchEvent(new Event('input', { bubbles: true }));
      state.applied = false;
    }
    stopRecognition();
    if (button) { setTimeout(function () { start(button); }, 220); }
  }

  document.addEventListener('DOMContentLoaded', function () {
    grabElements();

    document.querySelectorAll('[data-voice]').forEach(function (button) {
      if (!isSupported()) {
        button.disabled = true;
        button.title = 'مرورگر شما از ورودی صوتی پشتیبانی نمی‌کند';
      }
      button.addEventListener('click', function () {
        if (state.active && state.button === button) {
          stopRecognition();
          return;
        }
        start(button);
      });
    });

    if (acceptBtn) {
      acceptBtn.addEventListener('click', function () {
        if (!state.applied && state.lastTranscript) { applyResult(state.lastTranscript); }
        finish();
      });
    }
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function () {
        if (!state.active && state.lastTranscript !== '') { retry(); }
        else { revert(); }
      });
    }
    if (overlay) {
      overlay.addEventListener('click', function (event) {
        if (event.target === overlay) { finish(); }
      });
    }
  });

  global.KhoneVoice = {
    isSupported: isSupported,
    start: start,
    stop: stopRecognition
  };
})(window);
