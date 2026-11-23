const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

const html = readFileSync('vercel-deploy/index.html', 'utf8');
const script = html.match(/\(\(\) => \{[\s\S]*?\n    \}\)\(\);/)[0];

function bridge() {
    const target = () => ({ handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; } });
    const canvas = Object.assign(target(), {
        getBoundingClientRect: () => ({ width: 693, height: 390, left: 75, right: 768, bottom: 390 })
    });
    const window = Object.assign(target(), {
        visualViewport: target(), matchMedia: () => ({ matches: false, addEventListener() {} })
    });
    const document = Object.assign(target(), { getElementById: () => canvas, body: {}, hidden: false });
    vm.runInNewContext(script, {
        window, document, navigator: { maxTouchPoints: 0 }, innerWidth: 844, innerHeight: 390,
        getComputedStyle: () => ({ paddingLeft: '44px', paddingRight: '44px', paddingBottom: '21px' }),
        ResizeObserver: class { observe() {} }
    });
    return { canvas, window, document, read: () => JSON.parse(window.coinstrikeTouch.snapshot) };
}

test('touch detection and safe areas use the displayed canvas', () => {
    const b = bridge();
    assert.equal(b.read().touch, false);
    b.canvas.handlers.touchstart();
    assert.equal(b.read().touch, true);
    assert.equal(b.read().width, 693);
    assert.equal(b.read().left, 0);
    assert.equal(b.read().right, 0);
    assert.equal(b.read().bottom, 21);
});

test('releasing a touch outside does not cancel other held fingers', () => {
    const b = bridge();
    b.window.handlers.pointerup({ pointerType: 'touch', clientX: 900, clientY: 450 });
    assert.equal(b.read().reset, 0);
    b.window.handlers.pointerup({ pointerType: 'mouse', clientX: 200, clientY: 200 });
    assert.equal(b.read().reset, 0);
    b.window.handlers.pointerup({ pointerType: 'mouse', clientX: 900, clientY: 450 });
    assert.equal(b.read().reset, 1);
});

test('browser lifecycle cancellations reset held virtual inputs', () => {
    const b = bridge();
    b.canvas.handlers.touchcancel();
    b.window.handlers.blur();
    b.window.handlers.resize();
    b.window.visualViewport.handlers.resize();
    b.document.hidden = true;
    b.document.handlers.visibilitychange();
    assert.equal(b.read().reset, 5);
});
