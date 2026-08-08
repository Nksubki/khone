/* =========================================================================
   KhoneVoice — ورودی صوتی فارسی (تبدیل گفتار به متن و عدد)

   طراحی‌شده برای کار درست روی سافاری آیفون:
     • پنل وضعیت بلافاصله با لمس دکمه باز می‌شود (نه بعد از شروع ضبط)
     • اگر صفحه HTTPS نباشد، دلیل و راه‌حل را با زبان ساده می‌گوید
     • اگر اجازه میکروفون داده نشده باشد، دکمه «اجازه دسترسی» نشان می‌دهد
     • بعد از گرفتن اجازه، شروع ضبط با لمس کاربر انجام می‌شود
       (سافاری اجازه شروع خودکار نمی‌دهد)
     • چند حدسِ تشخیص گفتار نمایش داده می‌شود تا کاربر درست را انتخاب کند
   ========================================================================= */
(function (global) {
  'use strict';

  var Recognition = global.SpeechRecognition || global.webkitSpeechRecognition;

  var IOS_TIP =
    'راه مطمئن روی آیفون: روی خودِ فیلد ضربه بزنید تا کیبورد باز شود، ' +
    'بعد آیکن میکروفون کیبورد آیفون را بزنید و بگویید «صد و بیست میلیون». ' +
    'برنامه همان متن فارسی را خودش به عدد تبدیل می‌کند. ' +
    '(کیبورد فارسی نصب و Dictation در Settings › General › Keyboard روشن باشد.)';

  var elements = {};
  var state = {
    mode: 'text',
    input: null,
    button: null,
    previousValue: '',
    lastTranscript: '',
    alternatives: [],
    recognition: null,
    listening: false,
    applied: false,
    startTimer: null
  };

  // ------------------------------------------------------------------ //
  //  بررسی محیط
  // ------------------------------------------------------------------ //
  function isLocalHost() {
    var host = global.location ? global.location.hostname : '';
    return host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host === '::1';
  }

  function isSecure() {
    if (global.isSecureContext === true) { return true; }
    if (global.location && global.location.protocol === 'https:') { return true; }
    return isLocalHost();
  }

  function support() {
    if (!isSecure()) {
      return {
        ok: false,
        reason: 'insecure',
        message:
          'مرورگرها اجازه استفاده از میکروفون را فقط در آدرس‌های امن (HTTPS) می‌دهند. ' +
          'الان برنامه با آدرس http باز شده، به همین دلیل میکروفون باز نمی‌شود.'
      };
    }
    if (!Recognition) {
      return {
        ok: false,
        reason: 'unsupported',
        message:
          'این مرورگر از تبدیل گفتار به متن پشتیبانی نمی‌کند. ' +
          'روی آیفون از Safari و روی اندروید/ویندوز از Chrome استفاده کنید.'
      };
    }
    return { ok: true, reason: 'ok', message: 'ورودی صوتی در این مرورگر فعال است.' };
  }

  // ------------------------------------------------------------------ //
  //  عناصر پنل
  // ------------------------------------------------------------------ //
  function grab() {
    elements.overlay = document.getElementById('voice-overlay');
    elements.title = document.getElementById('voice-title');
    elements.transcript = document.getElementById('voice-transcript');
    elements.parsed = document.getElementById('voice-parsed');
    elements.accept = document.getElementById('voice-accept');
    elements.retry = document.getElementById('voice-retry');
    elements.cancel = document.getElementById('voice-cancel');
    elements.help = document.getElementById('voice-help');
    elements.permission = document.getElementById('voice-permission');
    elements.alts = document.getElementById('voice-alts');
    elements.altsList = document.getElementById('voice-alts-list');
    elements.pulse = document.getElementById('voice-pulse');
  }

  function setText(node, text) {
    if (node) { node.textContent = text || ''; }
  }

  function show(node, visible) {
    if (node) { node.hidden = !visible; }
  }

  function setPulse(active) {
    if (elements.pulse) { elements.pulse.classList.toggle('is-active', !!active); }
    if (state.button) { state.button.classList.toggle('recording', !!active); }
  }

  function openOverlay(titleText) {
    grab();
    if (!elements.overlay) { return; }
    elements.overlay.hidden = false;
    setText(elements.title, titleText || 'آماده…');
    setText(elements.transcript, '');
    setText(elements.parsed, '');
    setText(elements.help, '');
    show(elements.help, false);
    show(elements.permission, false);
    show(elements.alts, false);
    if (elements.altsList) { elements.altsList.innerHTML = ''; }
    setPulse(false);
  }

  function closeOverlay() {
    if (elements.overlay) { elements.overlay.hidden = true; }
    setPulse(false);
  }

  function showHelp(message, extra) {
    show(elements.help, true);
    if (elements.help) {
      elements.help.innerHTML = '';
      var main = document.createElement('p');
      main.textContent = message;
      elements.help.appendChild(main);
      if (extra) {
        var hint = document.createElement('p');
        hint.className = 'voice-tip';
        hint.textContent = extra;
        elements.help.appendChild(hint);
      }
    }
  }

  function setPermissionButton(mode) {
    if (!elements.permission) { return; }
    show(elements.permission, true);
    elements.permission.setAttribute('data-mode', mode);
    var label = elements.permission.querySelector('.btn-label');
    var text = mode === 'start' ? 'شروع ضبط' : 'اجازه دسترسی به میکروفون';
    if (label) { label.textContent = text; }
    else { elements.permission.textContent = text; }
  }

  // ------------------------------------------------------------------ //
  //  اعمال نتیجه
  // ------------------------------------------------------------------ //
  function markVoiceUsed() {
    var flag = document.getElementById('voice-used');
    if (flag) { flag.value = '1'; }
  }

  function fireInput(input) {
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function applyTranscript(transcript) {
    if (!state.input) { return false; }
    var text = (transcript || '').trim();
    if (!text) { return false; }

    if (state.mode === 'amount') {
      var value = global.KhoneNumber ? global.KhoneNumber.parse(text) : null;
      if (value === null) {
        setText(elements.parsed, 'عددی تشخیص داده نشد. یکی از حدس‌های زیر را انتخاب کنید یا دستی بنویسید.');
        return false;
      }
      state.input.value = global.KhoneNumber.format(value, false);
      fireInput(state.input);
      setText(
        elements.parsed,
        global.KhoneNumber.format(value, true) + ' تومان — ' + global.KhoneNumber.toWords(value)
      );
    } else {
      var normalized = global.KhoneNumber ? global.KhoneNumber.normalize(text) : text;
      var base = (state.previousValue || '').trim();
      state.input.value = base ? (base + ' ' + normalized) : normalized;
      fireInput(state.input);
      setText(elements.parsed, 'در فیلد نوشته شد.');
    }
    state.applied = true;
    markVoiceUsed();
    return true;
  }

  function restorePrevious() {
    if (state.applied && state.input) {
      state.input.value = state.previousValue;
      fireInput(state.input);
      state.applied = false;
    }
  }

  // ------------------------------------------------------------------ //
  //  انتخاب بهترین حدس (کمترین خطا)
  // ------------------------------------------------------------------ //
  function collectAlternatives(result) {
    var list = [];
    for (var i = 0; i < result.length; i++) {
      var item = result[i];
      if (!item || !item.transcript) { continue; }
      var text = item.transcript.trim();
      if (!text) { continue; }
      var duplicate = false;
      for (var j = 0; j < list.length; j++) {
        if (list[j].text === text) { duplicate = true; break; }
      }
      if (duplicate) { continue; }
      var value = global.KhoneNumber ? global.KhoneNumber.parse(text) : null;
      list.push({
        text: text,
        value: value,
        confidence: typeof item.confidence === 'number' ? item.confidence : 0
      });
    }
    return list;
  }

  function pickBest(list) {
    if (!list.length) { return null; }
    if (state.mode !== 'amount') { return list[0]; }

    var best = null;
    var bestScore = -1;
    for (var i = 0; i < list.length; i++) {
      var item = list[i];
      var score = 0;
      if (item.value !== null) {
        score += 100;
        if (global.KhoneNumber && global.KhoneNumber.roundnessScore) {
          score += global.KhoneNumber.roundnessScore(item.value) * 4;
        }
      }
      score += item.confidence * 10;
      score -= i * 0.5; // ترتیب پیشنهاد مرورگر هم کمی اهمیت دارد
      if (score > bestScore) {
        bestScore = score;
        best = item;
      }
    }
    return best || list[0];
  }

  function renderAlternatives(list) {
    if (!elements.altsList) { return; }
    elements.altsList.innerHTML = '';
    var shown = 0;
    for (var i = 0; i < list.length && shown < 5; i++) {
      var item = list[i];
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip voice-alt';
      if (state.mode === 'amount' && item.value !== null) {
        chip.textContent = global.KhoneNumber.format(item.value, true) + ' — «' + item.text + '»';
      } else {
        chip.textContent = item.text;
      }
      chip.setAttribute('data-text', item.text);
      chip.addEventListener('click', function (event) {
        restorePrevious();
        var text = event.currentTarget.getAttribute('data-text');
        setText(elements.transcript, text);
        applyTranscript(text);
        var siblings = elements.altsList.querySelectorAll('.voice-alt');
        for (var k = 0; k < siblings.length; k++) { siblings[k].classList.remove('chip-active'); }
        event.currentTarget.classList.add('chip-active');
      });
      elements.altsList.appendChild(chip);
      shown++;
    }
    show(elements.alts, shown > 1);
  }

  // ------------------------------------------------------------------ //
  //  ضبط
  // ------------------------------------------------------------------ //
  function stopRecognition(abort) {
    if (state.startTimer) {
      clearTimeout(state.startTimer);
      state.startTimer = null;
    }
    if (state.recognition) {
      try {
        state.recognition.onend = null;
        state.recognition.onresult = null;
        state.recognition.onerror = null;
        if (abort && state.recognition.abort) { state.recognition.abort(); }
        else { state.recognition.stop(); }
      } catch (e) { /* نادیده */ }
    }
    state.recognition = null;
    state.listening = false;
    setPulse(false);
  }

  function handleError(code) {
    var messages = {
      'not-allowed': 'اجازه دسترسی به میکروفون داده نشده است.',
      'service-not-allowed': 'سرویس تشخیص گفتار اجازه اجرا ندارد.',
      'audio-capture': 'میکروفونی پیدا نشد.',
      'no-speech': 'صدایی شنیده نشد.',
      'network': 'تشخیص گفتار به اینترنت نیاز دارد و شبکه در دسترس نیست.',
      'aborted': 'ضبط متوقف شد.'
    };
    setText(elements.title, 'مشکلی پیش آمد');
    setText(elements.transcript, messages[code] || ('خطا: ' + code));

    if (code === 'not-allowed' || code === 'service-not-allowed' || code === 'audio-capture') {
      showHelp(
        'برای فعال شدن میکروفون: در آیفون به Settings › Safari › Microphone بروید و ' +
        '«Allow» را انتخاب کنید. در صفحه هم روی دکمه زیر بزنید و اجازه را تأیید کنید.',
        IOS_TIP
      );
      setPermissionButton('ask');
    } else if (code === 'network') {
      showHelp('اتصال اینترنت را بررسی کنید؛ تشخیص گفتار مرورگر آنلاین انجام می‌شود.', IOS_TIP);
    }
  }

  function beginRecognition() {
    var recognition;
    try {
      recognition = new Recognition();
    } catch (e) {
      handleError('unsupported');
      return;
    }

    recognition.lang = 'fa-IR';
    recognition.continuous = false;
    recognition.interimResults = true;
    try { recognition.maxAlternatives = 5; } catch (e) { /* برخی مرورگرها ندارند */ }

    recognition.onstart = function () {
      state.listening = true;
      setPulse(true);
      if (state.startTimer) { clearTimeout(state.startTimer); state.startTimer = null; }
      setText(elements.title, state.mode === 'amount' ? 'مبلغ را بگویید…' : 'بفرمایید، در حال شنیدن…');
      setText(elements.transcript, 'گوش می‌دهم…');
      show(elements.permission, false);
      show(elements.help, false);
    };

    recognition.onresult = function (event) {
      var interim = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var result = event.results[i];
        if (result.isFinal) {
          var list = collectAlternatives(result);
          state.alternatives = list;
          var best = pickBest(list);
          if (best) {
            state.lastTranscript = best.text;
            setText(elements.transcript, best.text);
            applyTranscript(best.text);
            renderAlternatives(list);
          }
        } else {
          interim += result[0] ? result[0].transcript : '';
        }
      }
      if (interim) {
        setText(elements.transcript, interim);
        if (state.mode === 'amount' && global.KhoneNumber) {
          var guess = global.KhoneNumber.parse(interim);
          setText(elements.parsed, guess === null ? '' : global.KhoneNumber.format(guess, true) + ' تومان');
        }
      }
    };

    recognition.onerror = function (event) {
      state.listening = false;
      setPulse(false);
      handleError(event.error);
    };

    recognition.onend = function () {
      state.listening = false;
      setPulse(false);
      if (elements.overlay && !elements.overlay.hidden) {
        if (!state.lastTranscript) {
          if (elements.help && elements.help.hidden) {
            setText(elements.title, 'چیزی شنیده نشد');
            setText(elements.transcript, 'دکمه «تکرار» را بزنید و بلندتر و شفاف‌تر بگویید.');
          }
        } else {
          setText(elements.title, 'شنیدم');
        }
      }
    };

    state.recognition = recognition;

    try {
      recognition.start();
      setText(elements.transcript, 'در حال آماده‌سازی میکروفون…');
      // اگر ضبط شروع نشد (مثلاً پنجره اجازه باز نشد) بعد از ۲ ثانیه راهنما بده
      state.startTimer = setTimeout(function () {
        if (!state.listening) {
          setText(elements.title, 'میکروفون شروع نشد');
          setText(elements.transcript, 'اگر پنجره درخواست اجازه باز شد آن را تأیید کنید.');
          showHelp(
            'اگر پنجره‌ای باز نشد، احتمالاً اجازه میکروفون برای این سایت بسته است. ' +
            'دکمه زیر را بزنید و «Allow» را انتخاب کنید.',
            IOS_TIP
          );
          setPermissionButton('ask');
        }
      }, 2000);
    } catch (e) {
      handleError('not-allowed');
    }
  }

  function requestPermission() {
    setText(elements.transcript, 'در حال درخواست اجازه…');
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showHelp(
        'این مرورگر امکان درخواست اجازه میکروفون را نمی‌دهد. ' +
        'از تنظیمات مرورگر اجازه را دستی فعال کنید.',
        IOS_TIP
      );
      return;
    }
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(function (stream) {
        // بستن فوری جریان صدا؛ اگر باز بماند، تشخیص گفتار روی آیفون کار نمی‌کند
        stream.getTracks().forEach(function (track) { track.stop(); });
        setText(elements.title, 'اجازه داده شد');
        setText(elements.transcript, 'حالا دکمه «شروع ضبط» را بزنید و بگویید.');
        show(elements.help, false);
        setPermissionButton('start');
      })
      .catch(function () {
        showHelp(
          'اجازه داده نشد. در آیفون: Settings › Safari › Microphone › Allow ' +
          'و سپس صفحه را دوباره باز کنید.',
          IOS_TIP
        );
        setPermissionButton('ask');
      });
  }

  // ------------------------------------------------------------------ //
  //  شروع از دکمه میکروفون
  // ------------------------------------------------------------------ //
  function start(button) {
    grab();

    var selector = button.getAttribute('data-target');
    var input = selector ? document.querySelector(selector) : null;
    if (!input) { return; }

    // اگر همین دکمه در حال ضبط است، متوقف کن
    if (state.listening && state.button === button) {
      stopRecognition(false);
      return;
    }
    stopRecognition(true);

    state.mode = button.getAttribute('data-voice') === 'amount' ? 'amount' : 'text';
    state.input = input;
    state.button = button;
    state.previousValue = input.value || '';
    state.lastTranscript = '';
    state.alternatives = [];
    state.applied = false;

    // پنل بلافاصله باز می‌شود تا کاربر بداند چه خبر است
    openOverlay(state.mode === 'amount' ? 'مبلغ را بگویید…' : 'بفرمایید…');

    var environment = support();
    if (!environment.ok) {
      setText(elements.title, environment.reason === 'insecure' ? 'میکروفون در آدرس ناامن' : 'پشتیبانی نمی‌شود');
      setText(elements.transcript, environment.message);
      if (environment.reason === 'insecure') {
        showHelp(
          'دو راه‌حل: ۱) همین حالا از میکروفون کیبورد آیفون استفاده کنید. ' +
          '۲) برنامه را با آدرس HTTPS اجرا کنید (راهنمای README).',
          IOS_TIP
        );
      } else {
        showHelp('در این حالت می‌توانید از میکروفون کیبورد گوشی استفاده کنید.', IOS_TIP);
      }
      return;
    }

    beginRecognition();
  }

  // ------------------------------------------------------------------ //
  //  راه‌اندازی
  // ------------------------------------------------------------------ //
  document.addEventListener('DOMContentLoaded', function () {
    grab();
    var environment = support();

    // وضعیت میکروفون زیر فیلد مبلغ
    var note = document.getElementById('voice-note');
    if (note && !environment.ok) {
      note.hidden = false;
      note.textContent = environment.reason === 'insecure'
        ? 'میکروفون این دکمه فقط با آدرس HTTPS کار می‌کند. الان می‌توانید با میکروفونِ کیبورد گوشی داخل همین فیلد بگویید «صد و بیست میلیون» — خودش به عدد تبدیل می‌شود.'
        : 'این مرورگر ورودی صوتی ندارد؛ با میکروفون کیبورد گوشی بگویید «صد و بیست میلیون» — خودش به عدد تبدیل می‌شود.';
    }

    // وضعیت در صفحه «حساب من»
    var statusBox = document.getElementById('voice-status-box');
    if (statusBox) {
      statusBox.textContent = environment.ok
        ? 'ورودی صوتی فعال است. در فرم ثبت هزینه، دکمه میکروفون کنار مبلغ و توضیحات را بزنید.'
        : environment.message + ' ' + IOS_TIP;
    }

    document.querySelectorAll('[data-voice]').forEach(function (button) {
      if (!environment.ok) { button.classList.add('mic-warn'); }
      button.addEventListener('click', function () { start(button); });
    });

    if (elements.accept) {
      elements.accept.addEventListener('click', function () {
        if (!state.applied && state.lastTranscript) { applyTranscript(state.lastTranscript); }
        stopRecognition(true);
        closeOverlay();
      });
    }
    if (elements.retry) {
      elements.retry.addEventListener('click', function () {
        restorePrevious();
        state.lastTranscript = '';
        stopRecognition(true);
        openOverlay(state.mode === 'amount' ? 'مبلغ را بگویید…' : 'بفرمایید…');
        var environmentNow = support();
        if (environmentNow.ok) { beginRecognition(); }
        else { setText(elements.transcript, environmentNow.message); }
      });
    }
    if (elements.cancel) {
      elements.cancel.addEventListener('click', function () {
        restorePrevious();
        stopRecognition(true);
        closeOverlay();
      });
    }
    if (elements.permission) {
      elements.permission.addEventListener('click', function () {
        var mode = elements.permission.getAttribute('data-mode');
        if (mode === 'start') {
          show(elements.permission, false);
          beginRecognition();
        } else {
          requestPermission();
        }
      });
    }
    if (elements.overlay) {
      elements.overlay.addEventListener('click', function (event) {
        if (event.target === elements.overlay) {
          stopRecognition(true);
          closeOverlay();
        }
      });
    }
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && elements.overlay && !elements.overlay.hidden) {
        stopRecognition(true);
        closeOverlay();
      }
    });
  });

  global.KhoneVoice = {
    support: support,
    start: start,
    stop: function () { stopRecognition(true); }
  };
})(window);
