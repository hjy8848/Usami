"""Conservative, ID-neutral relational colour refinement with policy-derived bins.

These are structural grouping signatures, not a complete graph-isomorphism proof.
Raw numeric jitter, display labels, timestamps and simulator signatures do not add diversity.
"""
from usami_harness.models import digest

REFS={'org_id':'organizations','owner_id':'users','user_id':'users','customer_id':'users','project_id':'projects','invoice_id':'invoices',
 'warehouse_id':'warehouses','source_warehouse_id':'warehouses','target_warehouse_id':'warehouses','sku_id':'skus','lot_id':'lots',
 'source_lot_id':'lots','target_lot_id':'lots','notice_id':'receipt_notices','order_id':'orders','reservation_id':'reservations','reservation_ids':'reservations',
 'shipment_id':'shipments','guest_id':'guests','property_id':'properties','room_type_id':'room_types','room_type_ids':'room_types',
 'rate_plan_id':'rate_plans','room_id':'rooms','current_stay_id':'stays','subscription_id':'subscriptions','dependencies':'instances'}
CATEGORIES={'status','role','quality','category','returnable','receiving_enabled','housekeeping','maintenance','kind','outcome',
 'simulated_return_condition','simulated_identity_result','late_fee','auto_renew','plan_id','closed','payment_method','method','token'}


def relations(domain,world,permissions_only=False):
    raw=world.model_dump(mode='json');nodes={};edges={}
    allowed={'users','organizations','projects','warehouses','properties','access','memberships'}
    for collection,value in raw.items():
        if not isinstance(value,dict) or collection in {'rules','config'} or (permissions_only and collection not in allowed):continue
        for key,obj in value.items():
            if not isinstance(obj,dict) or 'id' not in obj:continue
            token=(collection,key);nodes[token]={'type':collection};edges[token]=[]
    def scan(token,value,prefix=''):
        if isinstance(value,dict):
            for field,item in value.items():
                if field in REFS:
                    values=item if isinstance(item,list) else [item]
                    for target in values:
                        right=(REFS[field],target) if isinstance(target,str) else None
                        if right in nodes:
                            edges[token].append((prefix+field,right));edges[right].append(('reverse:'+prefix+field,token))
                elif field in CATEGORIES and (not permissions_only or field=='role' or (field=='status' and token[0] in {'access','memberships'})):
                    nodes[token][prefix+field]=item
                elif isinstance(item,(list,dict)) and field not in {'attestation','gateway_notice','carrier_notice','receipt_notice','inspection_notice','receiving_notice','notice','payments','refunds'}:
                    scan(token,item,prefix+field+'.')
        elif isinstance(value,list):
            categories=[]
            for item in value:
                if isinstance(item,dict):
                    # List order is not a new business structure.
                    categories.append({k:v for k,v in item.items() if k in CATEGORIES})
                    scan(token,item,prefix+'item.')
            if categories:nodes[token][prefix+'categories']=sorted(categories,key=digest)
    for token in nodes:
        scan(token,raw[token[0]][token[1]])
        if not permissions_only:nodes[token].update(policy_features(domain,world,*token))
    colours={k:digest(v) for k,v in nodes.items()}
    base=dict(colours)
    for _ in range(6):colours={k:digest([base[k],sorted((label,colours[other]) for label,other in edges[k])]) for k in nodes}
    return digest({'version':'business-relations-v1','nodes':sorted(colours.values())})


def relation(a,b):return 'below' if a<b else 'equal' if a==b else 'above'


def policy_features(domain,w,collection,key):
    obj=getattr(w,collection)[key];features={}
    if domain=='cloudops':
        from usami_cloudops.rules import usage
        if collection=='projects':features['quota_usage']={k:relation(v,getattr(obj.quota,k)) for k,v in usage(w,key).items()}
        if collection=='instances':
            quota=w.projects[obj.project_id].quota
            features['fits_alone']=obj.cpu<=quota.cpu and obj.memory<=quota.memory and quota.instances>0
    elif domain=='fulfillment':
        from usami_fulfillment.rules import physical_volume,paid,price
        if collection=='warehouses':features['capacity']=relation(physical_volume(w,key),obj.capacity_volume)
        if collection=='lots':features['free_stock']='none' if obj.on_hand==obj.reserved else 'available';features['picked']=bool(obj.picked)
        if collection=='orders':
            features['paid']=relation(paid(w,key)-paid(w,key,'refund'),price(obj))
            features['line_stock']=sorted((relation(l.quantity-l.canceled,sum(lot.on_hand-lot.reserved for lot in w.lots.values() if lot.warehouse_id==obj.warehouse_id and lot.sku_id==l.sku_id and lot.quality=='available')),bool(l.canceled)) for l in obj.lines)
    elif domain=='stayops':
        from usami_stayops.rules import occupied,calendar_capacity,net_paid,cancellation_fee
        if collection=='calendar':features['occupancy']=relation(occupied(w,obj.room_type_id,obj.day),calendar_capacity(w,obj.room_type_id,obj.day));features['weekend']=obj.day.weekday()>=5
        if collection=='reservations':features.update(payment=relation(net_paid(w,key),obj.total_cents),deposit=relation(net_paid(w,key),obj.deposit_cents),arrival=relation(obj.arrival,w.clock.date()),cancel_fee='free' if not cancellation_fee(w,obj,w.clock) else 'penalty',hold_expired=w.clock>=obj.hold_expires_at)
        if collection=='rate_plans':features['deposit']='none' if not obj.deposit_bps else 'full' if obj.deposit_bps==10000 else 'partial';features['free_window']='none' if not obj.free_cancel_hours else 'positive'
    elif domain=='saas':
        if collection=='subscriptions':
            members=[m for m in w.memberships.values() if m.org_id==obj.org_id and m.status=='active'] if hasattr(obj,'org_id') else []
            features['seat_usage']=relation(len(members),obj.seats);features['expiry']=relation(obj.period_end,w.clock)
        if collection=='invoices':features['refundable']=bool(obj.refundable_amount_cents);features['refund_window']=bool(obj.paid_at and (w.clock-obj.paid_at).days<=w.rules.refund_window_days)
    return features


def signatures(domain,world):return {'structure':relations(domain,world),'permissions':relations(domain,world,True)}
