frappe.pages['alphax-pos'].on_page_load = function(wrapper) {
  frappe.ui.make_app_page({ parent: wrapper, title: 'AlphaX POS (Enterprise v0.4)', single_column: true });

  const LS_KEY = 'alphax_pos_offline_queue_v1';
  const state = { cart: [], payments: [], settings: null };

  const $root = $(wrapper).find('.layout-main-section');
  inject_css();
  $root.html(`
    <div class="p-3">
      <div class="d-flex align-items-center justify-content-between mb-2">
        <div>
          <div class="text-muted small">Barcode scan • Pricing rules • Offline queue • Shifts • Credit note redeem</div>
          <h3 class="mb-0">AlphaX POS</h3>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-default" data-action="shift_list">Shifts</button>
          <button class="btn btn-default" data-action="cash_moves">Cash Moves</button>
          <button class="btn btn-primary" data-action="sync_queue">Sync Queue</button>
        </div>
      </div>

      <div class="card mb-3"><div class="card-body">
        <div class="row">
          <div class="col-md-3"><label>Terminal</label><input class="form-control" data-field="terminal" placeholder="AlphaX POS Terminal"/></div>
          <div class="col-md-3"><label>Customer</label><input class="form-control" data-field="customer" placeholder="Customer"/></div>
          <div class="col-md-3"><label>Offer Code</label><input class="form-control" data-field="offer_code" placeholder="COUPON"/></div>
          <div class="col-md-3"><label>Scan / Item Code</label><input class="form-control" data-field="scan" placeholder="Scan barcode or type item code + Enter"/></div>
        </div>
        <div class="row mt-2">
          <div class="col-md-2"><label>Qty</label><input class="form-control" data-field="qty" type="number" value="1" min="1"/></div>
          <div class="col-md-10 d-flex align-items-end gap-2">
            <button class="btn btn-default" data-action="add_item">Add</button>
            <button class="btn btn-default" data-action="hold">Hold</button>
            <button class="btn btn-primary" data-action="submit">Pay & Submit</button>
            <button class="btn btn-danger" data-action="return">Return</button>
          </div>
        </div>
      </div></div>

      <div class="row">
        <div class="col-md-7">
          <div class="card mb-3"><div class="card-body">
            <h4>Cart</h4>
            <div data-area="cart" class="mt-2"></div>
            <hr/>
            <div class="d-flex justify-content-between"><div class="text-muted">Total (UI)</div><div style="font-size:22px"><b data-area="total">0.00</b></div></div>
          </div></div>

          <div class="card"><div class="card-body">
            <div class="d-flex align-items-center justify-content-between">
              <h4 class="mb-0">Payments</h4>
              <button class="btn btn-default btn-sm" data-action="add_credit_note">Redeem Credit Note</button>
            </div>
            <div class="row mt-2">
              <div class="col-md-4"><label>Mode of Payment</label><select class="form-control" data-field="mop"></select><small class="text-muted">Loaded from ERPNext Mode of Payment</small></div>
              <div class="col-md-4"><label>Amount</label><input class="form-control" data-field="amt" type="number"/></div>
              <div class="col-md-4 d-flex align-items-end"><button class="btn btn-default w-100" data-action="add_payment">Add Payment</button></div>
            </div>
            <div class="mt-3" data-area="payments"></div>
          </div></div>
        </div>

        <div class="col-md-5">
          <div class="card"><div class="card-body">
            <h4>Held Invoices</h4>
            <button class="btn btn-default btn-sm" data-action="refresh_holds">Refresh</button>
            <div class="mt-2" data-area="holds"></div>
          </div></div>

          <div class="card mt-3"><div class="card-body">
            <h4>Offline Queue</h4>
            <button class="btn btn-default btn-sm" data-action="show_queue">Show</button>
            <button class="btn btn-danger btn-sm" data-action="clear_queue">Clear</button>
            <div class="mt-2" data-area="queue"></div>
          </div></div>
        </div>
      </div>
    </div>
  `);

  function get_queue(){ try { return JSON.parse(localStorage.getItem(LS_KEY)||'[]'); } catch(e){ return []; } }
  function set_queue(q){ localStorage.setItem(LS_KEY, JSON.stringify(q||[])); }
  function queue_push(payload){ const q=get_queue(); q.push({id:frappe.utils.get_random(10), created_on:new Date().toISOString(), payload}); set_queue(q); }

  function ui_total(){
    let t=0; state.cart.forEach(r=>t += (r.qty*r.rate));
    $(wrapper).find('[data-area="total"]').text(t.toFixed(2));
    return t;
  }

  function render_cart(){
    const $c=$(wrapper).find('[data-area="cart"]');
    if(!state.cart.length){ $c.html('<div class="text-muted">No items.</div>'); ui_total(); return; }
    $c.html(state.cart.map((r,idx)=>`
      <div class="d-flex align-items-center justify-content-between border-bottom py-2">
        <div><b>${frappe.utils.escape_html(r.item_code)}</b><div class="text-muted small">Rate: ${r.rate} • Qty: ${r.qty}</div></div>
        <div class="d-flex gap-2">
          <button class="btn btn-xs btn-default" data-action="dec" data-idx="${idx}">-</button>
          <button class="btn btn-xs btn-default" data-action="inc" data-idx="${idx}">+</button>
          <button class="btn btn-xs btn-danger" data-action="rm" data-idx="${idx}">x</button>
        </div>
      </div>
    `).join(''));
    ui_total();
  }

  function render_payments(){
    const $p=$(wrapper).find('[data-area="payments"]');
    if(!state.payments.length){ $p.html('<div class="text-muted">No payments.</div>'); return; }
    $p.html(state.payments.map((p,idx)=>{
      const title=p.payment_type==='Credit Note Redeem' ? `Credit Note: ${p.credit_note} (Avail: ${p.credit_available})` : p.mode_of_payment;
      return `<div class="d-flex align-items-center justify-content-between border-bottom py-2">
        <div><b>${frappe.utils.escape_html(title)}</b><div class="text-muted small">Amount: ${p.amount}</div></div>
        <button class="btn btn-xs btn-danger" data-action="rm_pay" data-idx="${idx}">x</button>
      </div>`;
    }).join(''));
  }

  
async function load_mops(){
  const $sel=$(wrapper).find('[data-field="mop"]');
  $sel.html('<option value="">Select…</option>');
  try{
    const res=await frappe.call({
      method:'frappe.client.get_list',
      args:{doctype:'Mode of Payment', fields:['name','type','enabled'], filters:{enabled:1}, limit_page_length:200, order_by:'name asc'}
    });
    (res.message||[]).forEach(r=>{
      $sel.append(`<option value="${frappe.utils.escape_html(r.name)}">${frappe.utils.escape_html(r.name)}</option>`);
    });
  }catch(e){
    // fallback options
    ['Cash','Debit Card','Credit Card','MADA','STC Pay'].forEach(x=>$sel.append(`<option value="${x}">${x}</option>`));
  }
}

async function load_settings(){
    try{
      const r=await frappe.call({method:'frappe.client.get', args:{doctype:'AlphaX POS Settings', name:'AlphaX POS Settings'}});
      state.settings=r.message;
    }catch(e){}
  }

  async function pricing_get(item_code){
    try{
      const terminal=$(wrapper).find('[data-field="terminal"]').val().trim();
      const customer=$(wrapper).find('[data-field="customer"]').val().trim();
      let company=null, price_list=null;
      if(terminal){
        const t=await frappe.db.get_value('AlphaX POS Terminal', terminal, ['pos_outlet']);
        if(t && t.message && t.message.pos_outlet){
          const o=await frappe.db.get_value('AlphaX POS Outlet', t.message.pos_outlet, ['company','default_price_list']);
          company=o.message.company; price_list=o.message.default_price_list;
        }
      }
      const res=await frappe.call({ method:'erpnext.stock.get_item_details.get_item_details', args:{ args:{ item_code, qty:1, company, customer, price_list } } });
      const det=res.message||{};
      return det.rate || det.price_list_rate || 1;
    }catch(e){ return 1; }
  }

  async function add_item(){
    const code=$(wrapper).find('[data-field="scan"]').val().trim();
    const qty=parseFloat($(wrapper).find('[data-field="qty"]').val()||1);
    if(!code) return;
    const rate=await pricing_get(code);
    state.cart.push({item_code:code, qty, rate});
    $(wrapper).find('[data-field="scan"]').val('');
    render_cart();
  }

  async function refresh_holds(){
    const $h=$(wrapper).find('[data-area="holds"]');
    $h.html('<div class="text-muted">Loading…</div>');
    const res=await frappe.call({ method:'frappe.client.get_list',
      args:{ doctype:'AlphaX POS Order', fields:['name','customer','modified'], filters:{docstatus:0, order_status:'Hold'}, order_by:'modified desc', limit_page_length:20 }});
    const rows=(res.message||[]).map(d=>`
      <div class="border-bottom py-2">
        <div><b>${d.name}</b></div>
        <div class="text-muted small">${d.customer||''}</div>
        <a class="btn btn-xs btn-default mt-1" href="#Form/AlphaX POS Order/${d.name}">Open</a>
      </div>
    `).join('');
    $h.html(rows || '<div class="text-muted">No held invoices.</div>');
  }

  function render_queue(){
    const q=get_queue();
    const $q=$(wrapper).find('[data-area="queue"]');
    if(!q.length){ $q.html('<div class="text-muted">Queue empty.</div>'); return; }
    $q.html(q.map(x=>`
      <div class="border-bottom py-2">
        <div><b>${x.id}</b> <span class="text-muted small">${x.created_on}</span></div>
        <div class="text-muted small">${frappe.utils.escape_html(JSON.stringify(x.payload).slice(0,120))}…</div>
      </div>
    `).join(''));
  }

  async function sync_queue(){
    const q=get_queue();
    if(!q.length) return frappe.msgprint('Queue is empty.');
    let ok=0, fail=0; const remaining=[];
    for(const it of q){
      try{
        const ins=await frappe.call({method:'frappe.client.insert', args:{doc: it.payload.doc}});
        const name=ins.message.name;
        if(it.payload.submit){
          await frappe.call({method:'frappe.client.submit', args:{doc:{doctype:'AlphaX POS Order', name}}});
        }
        ok++;
      }catch(e){ fail++; remaining.push(it); }
    }
    set_queue(remaining); render_queue();
  boot_from_terminal();
    frappe.msgprint(`Sync complete. Success: ${ok}, Failed: ${fail}`);
  }

  async function add_credit_note(){
    const total=ui_total();
    const already=state.payments.filter(p=>p.payment_type==='Credit Note Redeem').reduce((s,p)=>s+(p.amount||0),0);
    const remaining=Math.max(0, total - already);

    const d=new frappe.ui.Dialog({
      title:'Redeem Credit Note',
      fields:[
        {fieldname:'credit_note', label:'Credit Note No (scan or enter)', fieldtype:'Data', reqd:1},
        {fieldname:'amount', label:'Amount', fieldtype:'Currency', reqd:1, read_only:1},
        {fieldname:'allow_edit', label:'Allow edit amount', fieldtype:'Check', default: (state.settings && state.settings.allow_edit_credit_note_amount) ? 1 : 0}
      ],
      primary_action_label:'Add',
      primary_action: async (v)=>{
        const cn=(v.credit_note||'').trim();
        const r=await frappe.call({method:'alphax_pos_suite.alphax_pos_suite.pos.redemption.get_credit_note_available', args:{credit_note: cn}});
        const avail=(r.message && r.message.available) || 0;
        let amt=Math.min(avail, remaining);
        const can_edit = !!(state.settings && state.settings.allow_edit_credit_note_amount) && !!v.allow_edit;
        if(can_edit){ amt = Math.min(parseFloat(v.amount||amt), avail, remaining); }
        state.payments.push({payment_type:'Credit Note Redeem', credit_note: cn, credit_available: avail, amount: amt});
        render_payments(); d.hide();
      }
    });
    d.show();

    d.fields_dict.credit_note.$input.on('keydown', async (e)=>{
      if(e.key!=='Enter') return;
      const cn=d.get_value('credit_note');
      if(!cn) return;
      const r=await frappe.call({method:'alphax_pos_suite.alphax_pos_suite.pos.redemption.get_credit_note_available', args:{credit_note: cn}});
      const avail=(r.message && r.message.available) || 0;
      d.set_value('amount', Math.min(avail, remaining));
      const can_edit = !!(state.settings && state.settings.allow_edit_credit_note_amount) && !!d.get_value('allow_edit');
      d.set_df_property('amount','read_only', can_edit ? 0 : 1);
    });
  }

  function add_payment(){
    const mop=$(wrapper).find('[data-field="mop"]').val().trim();
    const amt=parseFloat($(wrapper).find('[data-field="amt"]').val()||0);
    if(!mop || !amt) return frappe.msgprint('Enter Mode of Payment and Amount');
    state.payments.push({payment_type:'Payment', mode_of_payment:mop, amount:amt});
    $(wrapper).find('[data-field="mop"]').val('');
    $(wrapper).find('[data-field="amt"]').val('');
    render_payments();
  }

  async function create_order({hold=false, submit=false, is_return=false}){
    const terminal=$(wrapper).find('[data-field="terminal"]').val().trim();
    const customer=$(wrapper).find('[data-field="customer"]').val().trim();
    const offer=$(wrapper).find('[data-field="offer_code"]').val().trim();
    if(!terminal) return frappe.msgprint('Terminal is required');
    if(!customer) return frappe.msgprint('Customer is required');
    if(!state.cart.length) return frappe.msgprint('Add at least one item');

    let return_against=null, return_reason=null;
    if(is_return){
      const v=await new Promise(resolve=>{
        const d=new frappe.ui.Dialog({
          title:'Return Invoice',
          fields:[
            {fieldname:'return_against', label:'Return Against Invoice (scan or enter)', fieldtype:'Data', reqd:1},
            {fieldname:'return_reason', label:'Return Reason', fieldtype:'Link', options:'AlphaX POS Return Reason'}
          ],
          primary_action_label:'Continue',
          primary_action:(vals)=>{ d.hide(); resolve(vals); }
        });
        d.show();
      });
      return_against=v.return_against;
      return_reason=v.return_reason;
    }

    const doc={
      doctype:'AlphaX POS Order',
      client_uuid: frappe.utils.get_random(20),
      client_device: navigator.userAgent,
      pos_terminal: terminal,
      customer: customer,
      posting_date: frappe.datetime.nowdate(),
      posting_time: frappe.datetime.now_time(),
      order_status: hold ? 'Hold' : 'Active',
      offer_code: offer,
      is_return: is_return ? 1 : 0,
      return_against: return_against,
      return_reason: return_reason,
      items: state.cart.map(r=>({doctype:'AlphaX POS Order Item', item_code:r.item_code, qty:r.qty, rate:r.rate})),
      payments: state.payments.map(p=>{
        if(p.payment_type==='Credit Note Redeem') return {doctype:'AlphaX POS Payment', payment_type:'Credit Note Redeem', credit_note:p.credit_note, amount:p.amount};
        return {doctype:'AlphaX POS Payment', payment_type:'Payment', mode_of_payment:p.mode_of_payment, amount:p.amount};
      })
    };

    try{
      const ins=await frappe.call({method:'frappe.client.insert', args:{doc}});
      const name=ins.message.name;
      if(submit && !hold){
        await frappe.call({method:'frappe.client.submit', args:{doc:{doctype:'AlphaX POS Order', name}}});
        frappe.msgprint(`Submitted POS Order ${name}`);
      } else {
        frappe.msgprint(`Saved POS Order ${name}`);
      }
      state.cart=[]; state.payments=[];
      render_cart(); render_payments(); refresh_holds();
    }catch(e){
      queue_push({doc, submit: submit && !hold});
      render_queue();
      frappe.msgprint('Posting failed. Saved to offline queue.');
    }
  }

  $(wrapper).on('keydown','[data-field="scan"]', async (e)=>{ if(e.key==='Enter') await add_item(); });
  $(wrapper).on('click','[data-action="add_item"]', add_item);
  $(wrapper).on('click','[data-action="inc"]', function(){ const i=parseInt($(this).attr('data-idx')); state.cart[i].qty+=1; render_cart(); });
  $(wrapper).on('click','[data-action="dec"]', function(){ const i=parseInt($(this).attr('data-idx')); state.cart[i].qty=Math.max(1,state.cart[i].qty-1); render_cart(); });
  $(wrapper).on('click','[data-action="rm"]', function(){ const i=parseInt($(this).attr('data-idx')); state.cart.splice(i,1); render_cart(); });

  $(wrapper).on('click','[data-action="add_payment"]', add_payment);
  $(wrapper).on('click','[data-action="rm_pay"]', function(){ const i=parseInt($(this).attr('data-idx')); state.payments.splice(i,1); render_payments(); });
  $(wrapper).on('click','[data-action="add_credit_note"]', add_credit_note);

  $(wrapper).on('click','[data-action="hold"]', ()=>create_order({hold:true, submit:false}));
  $(wrapper).on('click','[data-action="submit"]', ()=>create_order({hold:false, submit:true}));
  $(wrapper).on('click','[data-action="return"]', ()=>create_order({hold:false, submit:true, is_return:true}));

  $(wrapper).on('click','[data-action="refresh_holds"]', refresh_holds);
  $(wrapper).on('click','[data-action="show_queue"]', render_queue);
  $(wrapper).on('click','[data-action="clear_queue"]', ()=>{ set_queue([]); render_queue(); });
  $(wrapper).on('click','[data-action="sync_queue"]', sync_queue);

  $(wrapper).on('click','[data-action="shift_list"]', ()=>frappe.set_route('List','AlphaX POS Shift'));
  $(wrapper).on('click','[data-action="cash_moves"]', ()=>frappe.set_route('List','AlphaX POS Cash Movement'));

  async function boot_from_terminal(){
    const terminal = $(wrapper).find('[data-field="terminal"]').val().trim();
    if(!terminal) return;
    try{
        const r = await frappe.call({method:'alphax_pos_suite.alphax_pos_suite.api.get_pos_boot', args:{terminal}});
        const boot = r.message || {};
        state.boot = boot;
        state.profile = boot.profile || {};
        state.theme = boot.theme || null;
        state.allowed_mops = boot.payment_methods || [];
        state.scale = boot.scale || {generic:null, prefix_map:[]};
        apply_theme(state.theme);
        await load_mops();
        render_mop_tiles();
    }catch(e){
        // ignore
    }
}

load_settings(); load_mops(); render_cart(); render_payments(); refresh_holds(); render_queue();
};
