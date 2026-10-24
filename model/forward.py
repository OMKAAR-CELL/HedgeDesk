def forward_rate(spot, days, r_foreign, r_inr, spread=0.001):
    if r_foreign is None or r_inr is None:
        return None
    t=days/365
    rate = spot*(1+t*r_inr)/(1+t*r_foreign)
    return rate * (1 - spread)
 

