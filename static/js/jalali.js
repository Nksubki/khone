/* =========================================================================
   KhoneDate — تبدیل تاریخ میلادی/شمسی + تقویم فارسی سبک (بدون کتابخانه)
   ========================================================================= */
(function (global) {
  'use strict';

  var MONTH_NAMES = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];
  var DOW_SHORT = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
  var G_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

  function toEnglishDigits(text) {
    return (global.KhoneNumber ? global.KhoneNumber.toEnglishDigits(text) : String(text));
  }
  function toPersianDigits(text) {
    return (global.KhoneNumber ? global.KhoneNumber.toPersianDigits(text) : String(text));
  }

  /** میلادی → شمسی */
  function g2j(gy, gm, gd) {
    var jy;
    gy = parseInt(gy, 10); gm = parseInt(gm, 10); gd = parseInt(gd, 10);
    if (gy > 1600) { jy = 979; gy -= 1600; } else { jy = 0; gy -= 621; }
    var gy2 = (gm > 2) ? (gy + 1) : gy;
    var days = (365 * gy) + Math.floor((gy2 + 3) / 4) - Math.floor((gy2 + 99) / 100)
      + Math.floor((gy2 + 399) / 400) - 80 + gd + G_DAYS[gm - 1];
    jy += 33 * Math.floor(days / 12053);
    days %= 12053;
    jy += 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days > 365) {
      jy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }
    var jm, jd;
    if (days < 186) {
      jm = 1 + Math.floor(days / 31);
      jd = 1 + (days % 31);
    } else {
      jm = 7 + Math.floor((days - 186) / 30);
      jd = 1 + ((days - 186) % 30);
    }
    return [jy, jm, jd];
  }

  /** شمسی → میلادی */
  function j2g(jy, jm, jd) {
    var gy;
    jy = parseInt(jy, 10); jm = parseInt(jm, 10); jd = parseInt(jd, 10);
    if (jy > 979) { gy = 1600; jy -= 979; } else { gy = 621; }
    var days = (365 * jy) + (Math.floor(jy / 33) * 8) + Math.floor(((jy % 33) + 3) / 4)
      + 78 + jd + ((jm < 7) ? ((jm - 1) * 31) : (((jm - 7) * 30) + 186));
    gy += 400 * Math.floor(days / 146097);
    days %= 146097;
    if (days > 36524) {
      days -= 1;
      gy += 100 * Math.floor(days / 36524);
      days %= 36524;
      if (days >= 365) { days += 1; }
    }
    gy += 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days > 365) {
      gy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }
    var gd = days + 1;
    var leap = ((gy % 4 === 0) && (gy % 100 !== 0)) || (gy % 400 === 0);
    var monthDays = [0, 31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    var gm = 12;
    for (var m = 1; m <= 12; m++) {
      if (gd <= monthDays[m]) { gm = m; break; }
      gd -= monthDays[m];
    }
    return [gy, gm, gd];
  }

  function isLeap(jy) {
    var g = j2g(jy, 12, 30);
    var back = g2j(g[0], g[1], g[2]);
    return back[0] === jy && back[1] === 12 && back[2] === 30;
  }

  function monthDays(jy, jm) {
    if (jm <= 6) { return 31; }
    if (jm <= 11) { return 30; }
    return isLeap(jy) ? 30 : 29;
  }

  /** تاریخ امروز به وقت تهران (مستقل از ساعت دستگاه) */
  function tehranNow() {
    var now = new Date();
    try {
      var parts = new Intl.DateTimeFormat('en-US', {
        timeZone: 'Asia/Tehran',
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false
      }).formatToParts(now);
      var map = {};
      parts.forEach(function (part) { map[part.type] = part.value; });
      return {
        gy: parseInt(map.year, 10),
        gm: parseInt(map.month, 10),
        gd: parseInt(map.day, 10),
        hour: parseInt(map.hour, 10) % 24,
        minute: parseInt(map.minute, 10)
      };
    } catch (e) {
      return {
        gy: now.getFullYear(), gm: now.getMonth() + 1, gd: now.getDate(),
        hour: now.getHours(), minute: now.getMinutes()
      };
    }
  }

  function todayJalali() {
    var t = tehranNow();
    return g2j(t.gy, t.gm, t.gd);
  }

  function pad(number) { return (number < 10 ? '0' : '') + number; }

  function formatJalali(parts) {
    return parts[0] + '/' + pad(parts[1]) + '/' + pad(parts[2]);
  }

  function formatLong(parts) {
    return toPersianDigits(parts[2] + ' ' + MONTH_NAMES[parts[1] - 1] + ' ' + parts[0]);
  }

  /** «۱۴۰۵/۰۵/۱۷» → [1405, 5, 17] یا null */
  function parseInput(text) {
    if (!text) { return null; }
    var raw = toEnglishDigits(String(text)).trim();
    var pieces = raw.split(/[^0-9]+/).filter(function (piece) { return piece !== ''; });
    if (pieces.length !== 3) { return null; }
    var jy = parseInt(pieces[0], 10);
    var jm = parseInt(pieces[1], 10);
    var jd = parseInt(pieces[2], 10);
    if (jy < 100) { jy += 1400; }
    if (!jy || !jm || !jd || jm < 1 || jm > 12) { return null; }
    if (jd < 1 || jd > monthDays(jy, jm)) { return null; }
    return [jy, jm, jd];
  }

  /** جابه‌جایی روزانه با حفظ صحت تقویم */
  function addDays(parts, delta) {
    var g = j2g(parts[0], parts[1], parts[2]);
    var date = new Date(Date.UTC(g[0], g[1] - 1, g[2]));
    date.setUTCDate(date.getUTCDate() + delta);
    return g2j(date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate());
  }

  /** شنبه = 0 ... جمعه = 6 */
  function weekdayIndex(parts) {
    var g = j2g(parts[0], parts[1], parts[2]);
    var date = new Date(Date.UTC(g[0], g[1] - 1, g[2]));
    return (date.getUTCDay() + 1) % 7;
  }

  /* ======================================================================
     تقویم (Date Picker)
     ====================================================================== */
  var activePicker = null;

  function closePicker() {
    if (activePicker) {
      if (activePicker.el && activePicker.el.parentNode) {
        activePicker.el.parentNode.removeChild(activePicker.el);
      }
      if (activePicker.backdrop && activePicker.backdrop.parentNode) {
        activePicker.backdrop.parentNode.removeChild(activePicker.backdrop);
      }
    }
    activePicker = null;
  }

  function buildPicker(input) {
    var selected = parseInput(input.value) || todayJalali();
    var view = { y: selected[0], m: selected[1] };
    var today = todayJalali();

    var box = document.createElement('div');
    box.className = 'jdp';

    function render() {
      box.innerHTML = '';

      var head = document.createElement('div');
      head.className = 'jdp-head';

      var prev = document.createElement('button');
      prev.type = 'button';
      prev.className = 'jdp-nav';
      prev.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-chevron-right"></use></svg>';
      prev.title = 'ماه قبل';
      prev.addEventListener('click', function () {
        view.m -= 1;
        if (view.m < 1) { view.m = 12; view.y -= 1; }
        render();
      });

      var next = document.createElement('button');
      next.type = 'button';
      next.className = 'jdp-nav';
      next.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-chevron-left"></use></svg>';
      next.title = 'ماه بعد';
      next.addEventListener('click', function () {
        view.m += 1;
        if (view.m > 12) { view.m = 1; view.y += 1; }
        render();
      });

      var title = document.createElement('div');
      title.className = 'jdp-title';
      title.textContent = MONTH_NAMES[view.m - 1] + ' ' + toPersianDigits(view.y);

      head.appendChild(prev);
      head.appendChild(title);
      head.appendChild(next);
      box.appendChild(head);

      var grid = document.createElement('div');
      grid.className = 'jdp-grid';
      DOW_SHORT.forEach(function (name) {
        var cell = document.createElement('div');
        cell.className = 'jdp-dow';
        cell.textContent = name;
        grid.appendChild(cell);
      });

      var firstWeekday = weekdayIndex([view.y, view.m, 1]);
      for (var i = 0; i < firstWeekday; i++) {
        var blank = document.createElement('div');
        blank.className = 'jdp-day empty';
        grid.appendChild(blank);
      }

      var total = monthDays(view.y, view.m);
      for (var day = 1; day <= total; day++) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'jdp-day';
        btn.textContent = toPersianDigits(day);
        if ((firstWeekday + day - 1) % 7 === 6) { btn.className += ' friday'; }
        if (view.y === today[0] && view.m === today[1] && day === today[2]) {
          btn.className += ' today';
        }
        if (view.y === selected[0] && view.m === selected[1] && day === selected[2]) {
          btn.className += ' selected';
        }
        btn.setAttribute('data-day', String(day));
        btn.addEventListener('click', function (event) {
          var chosen = parseInt(event.currentTarget.getAttribute('data-day'), 10);
          input.value = formatJalali([view.y, view.m, chosen]);
          input.dispatchEvent(new Event('change', { bubbles: true }));
          input.dispatchEvent(new Event('input', { bubbles: true }));
          closePicker();
        });
        grid.appendChild(btn);
      }
      box.appendChild(grid);

      var foot = document.createElement('div');
      foot.className = 'jdp-foot';

      var todayBtn = document.createElement('button');
      todayBtn.type = 'button';
      todayBtn.className = 'chip';
      todayBtn.textContent = 'امروز';
      todayBtn.addEventListener('click', function () {
        input.value = formatJalali(today);
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.dispatchEvent(new Event('input', { bubbles: true }));
        closePicker();
      });

      var clearBtn = document.createElement('button');
      clearBtn.type = 'button';
      clearBtn.className = 'chip chip-clear';
      clearBtn.textContent = 'بستن';
      clearBtn.addEventListener('click', closePicker);

      foot.appendChild(todayBtn);
      foot.appendChild(clearBtn);
      box.appendChild(foot);
    }

    render();
    return box;
  }

  function openPicker(input) {
    if (activePicker && activePicker.input === input) { closePicker(); return; }
    closePicker();

    var box = buildPicker(input);

    // روی موبایل: شیت پایین صفحه (بزرگ‌تر و راحت‌تر برای لمس)
    if (window.innerWidth < 560) {
      var backdrop = document.createElement('div');
      backdrop.className = 'jdp-backdrop';
      backdrop.addEventListener('click', closePicker);
      document.body.appendChild(backdrop);

      box.className = 'jdp jdp-sheet';
      document.body.appendChild(box);

      activePicker = { el: box, input: input, backdrop: backdrop };
      return;
    }

    document.body.appendChild(box);

    var rect = input.getBoundingClientRect();
    var top = rect.bottom + window.scrollY + 6;
    var width = box.offsetWidth || 290;
    var height = box.offsetHeight || 330;
    var left = rect.left + window.scrollX;
    if (left + width > window.innerWidth - 8) {
      left = Math.max(8, window.innerWidth - width - 8);
    }
    if (rect.bottom + height + 12 > window.innerHeight) {
      top = Math.max(window.scrollY + 8, rect.top + window.scrollY - height - 8);
    }
    box.style.top = top + 'px';
    box.style.left = left + 'px';

    activePicker = { el: box, input: input, backdrop: null };
  }

  document.addEventListener('click', function (event) {
    if (!activePicker) { return; }
    if (activePicker.el.contains(event.target)) { return; }
    if (event.target === activePicker.input) { return; }
    if (event.target.closest && event.target.closest('[data-open-calendar]')) { return; }
    closePicker();
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { closePicker(); }
  });

  global.KhoneDate = {
    g2j: g2j,
    j2g: j2g,
    isLeap: isLeap,
    monthDays: monthDays,
    monthNames: MONTH_NAMES,
    todayJalali: todayJalali,
    tehranNow: tehranNow,
    formatJalali: formatJalali,
    formatLong: formatLong,
    parseInput: parseInput,
    addDays: addDays,
    weekdayIndex: weekdayIndex,
    openPicker: openPicker,
    closePicker: closePicker
  };
})(window);
