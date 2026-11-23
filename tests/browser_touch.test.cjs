const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const html = readFileSync('vercel-deploy/index.html', 'utf8');
const script = html.match(/\(\(\) => \{[\s\S]*?\n    \}\)\(\);/)[0];

function bridge(options = {}) {
    const target = () => ({ handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; } });
    const safe = options.safe || {left:44, right:44, top:0, bottom:21};
    const calls = {fullscreen:0, locks:[], unlocks:0};
    const canvas = Object.assign(target(), {style:{}, width:1024, height:576,
        getBoundingClientRect() {
            const [left,top,width,height] = ['left','top','width','height'].map(k => parseFloat(this.style[k]) || 0);
            return {left,top,width,height,right:left+width,bottom:top+height};
        }
    });
    const entry = target(), rotate = target(), overlay = {hidden:true}, root = {};
    const elements = {canvas,infobox:entry,'rotate-overlay':overlay,'rotate-fullscreen':rotate};
    const document = Object.assign(target(), {getElementById:id => elements[id],documentElement:root,body:{},hidden:false});
    const orientation = Object.assign(target(), {
        async lock(value) { calls.locks.push(value); if (options.rejectLock) throw Error('unavailable'); },
        unlock() { calls.unlocks++; }
    });
    const window = Object.assign(target(), {
        innerWidth:options.width || 844, innerHeight:options.height || 390,
        visualViewport:Object.assign(target(), {width:options.width || 844,height:options.height || 390,offsetLeft:0,offsetTop:0}),
        matchMedia:query => ({matches:query === '(pointer: coarse)' ? !!options.primaryCoarse : !!options.coarse,addEventListener() {}}),
        screen:{orientation}
    });
    if (!options.noFullscreen) root.requestFullscreen = async () => {
        calls.fullscreen++;
        if (options.rejectFullscreen) throw Error('denied');
        document.fullscreenElement = root;
        document.handlers.fullscreenchange();
    };
    if (options.noOrientation) delete orientation.lock;
    vm.runInNewContext(script, {
        window,document,navigator:{maxTouchPoints:options.touchPoints || 0,
            userAgent:options.mobile ? 'Android Chrome' : 'Windows Chrome', platform:options.platform || 'Win32'},
        getComputedStyle:() => Object.fromEntries(Object.entries(safe).map(([k,v]) => ['padding'+k[0].toUpperCase()+k.slice(1),v+'px'])),
        ResizeObserver:class { observe() {} }
    });
    return {canvas,window,document,entry,rotate,overlay,calls,read:() => JSON.parse(window.coinstrikeTouch.snapshot),
        resize(width,height) {
            Object.assign(window,{innerWidth:width,innerHeight:height});
            Object.assign(window.visualViewport,{width,height});
            window.handlers.resize();
        }
    };
}

test('touch capability and safe-area canvas geometry', () => {
    const b = bridge();
    assert.equal(b.read().touch,false);
    b.canvas.handlers.touchstart();
    assert.equal(b.read().touch,true);
    const r = b.canvas.getBoundingClientRect();
    assert.ok(r.left >= 44 && r.right <= 800 && r.bottom <= 369);
    assert.ok(Math.abs(r.width/r.height - 16/9) < 1e-9);
    assert.equal(b.read().left,0); assert.equal(b.read().bottom,0);
});

test('releasing a touch outside does not cancel other fingers', () => {
    const b = bridge();
    b.window.handlers.pointerup({pointerType:'touch',clientX:900,clientY:450});
    assert.equal(b.read().reset,0);
    b.window.handlers.pointerup({pointerType:'mouse',clientX:200,clientY:200});
    assert.equal(b.read().reset,0);
    b.window.handlers.pointerup({pointerType:'mouse',clientX:900,clientY:450});
    assert.equal(b.read().reset,1);
});

test('browser lifecycle cancellations clear virtual inputs', () => {
    const b = bridge();
    b.canvas.handlers.touchcancel(); b.window.handlers.blur(); b.window.handlers.resize();
    b.window.visualViewport.handlers.resize();
    b.document.hidden = true; b.document.handlers.visibilitychange();
    assert.equal(b.read().reset,5);
});

test('maximal uniform fit preserves the logical framebuffer at every viewport', () => {
    const b = bridge({safe:{left:0,right:0,top:0,bottom:0}});
    for (const [w,h] of [[1366,768],[1440,900],[2560,1080],[844,390],[320,568]]) {
        b.resize(w,h);
        const r = b.canvas.getBoundingClientRect();
        assert.ok(Math.abs(r.width-Math.min(w,h*16/9)) < 1e-8);
        assert.ok(Math.abs(r.height-Math.min(h,w*9/16)) < 1e-8);
        assert.ok(r.left >= -1e-8 && r.top >= -1e-8 && r.right <= w+1e-8 && r.bottom <= h+1e-8);
        assert.deepEqual([b.canvas.width,b.canvas.height],[1024,576]);
    }
});

test('mobile portrait blocks play and manual rotation restores it', () => {
    const b = bridge({mobile:true,touchPoints:5,width:390,height:844});
    assert.equal(b.overlay.hidden,false); assert.equal(b.entry.disabled,true);
    assert.equal(b.read().portraitBlocked,true);
    b.resize(844,390);
    assert.equal(b.overlay.hidden,true); assert.equal(b.entry.disabled,false);
    assert.equal(b.read().portraitBlocked,false);
});

test('desktop portrait windows and touch laptops are not forced to rotate', () => {
    const b = bridge({touchPoints:5,width:640,height:900});
    assert.equal(b.read().touch,true); assert.equal(b.read().portraitBlocked,false);
    assert.equal(b.overlay.hidden,true);
});

test('fullscreen attempts once automatically and respects exit', async () => {
    const b = bridge();
    await b.entry.handlers.click(); await b.entry.handlers.click();
    assert.equal(b.calls.fullscreen,1);
    b.document.fullscreenElement = null; b.document.handlers.fullscreenchange();
    await b.entry.handlers.click(); assert.equal(b.calls.fullscreen,1);
    await b.rotate.handlers.click(); assert.equal(b.calls.fullscreen,2);
});

test('landscape lock is requested in fullscreen and released on exit', async () => {
    const b = bridge({mobile:true,touchPoints:1});
    await b.entry.handlers.click(); assert.deepEqual(b.calls.locks,['landscape']);
    b.document.fullscreenElement = null; b.document.handlers.fullscreenchange();
    assert.equal(b.calls.unlocks,1);
});

test('fullscreen and orientation failures preserve manual landscape fallback', async () => {
    for (const option of [{noFullscreen:true},{rejectFullscreen:true},{rejectLock:true},{noOrientation:true}]) {
        const b = bridge({mobile:true,touchPoints:1,width:390,height:844,...option});
        await b.rotate.handlers.click(); assert.equal(b.read().portraitBlocked,true);
        b.resize(844,390); assert.equal(b.read().portraitBlocked,false); assert.equal(b.overlay.hidden,true);
    }
});

test('visual viewport offsets and browser chrome resizing update the same fit', () => {
    const b = bridge({safe:{left:0,right:0,top:0,bottom:0}});
    Object.assign(b.window.visualViewport,{width:600,height:350,offsetLeft:12,offsetTop:20});
    b.window.visualViewport.handlers.resize();
    const r = b.canvas.getBoundingClientRect();
    assert.ok(r.left >= 12 && r.top >= 20 && r.right <= 612 && r.bottom <= 370);
    assert.equal(b.read().width,r.width);
});
