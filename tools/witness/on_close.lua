-- on_close.lua -- witness for proofs/hu-on-lower.md, gadget G_C (forced closing site, Lemma 3.2)
-- STATUS: written, NOT RUN. Harness conventions as in off_diag_push.lua (map-relative coords, OX/OY).
-- Claims checked: (a) branch cannot bypass N diagonally; (a) intended push W: N->Q and exit to (1,0);
-- (b,c) after closing, W can be driven to corner C but the forward part beyond C stays unreachable.
-- hunger=false only to keep the test short (instances keep hunger on).

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;

local function check(cond, msg) if (not cond) then error("G_C FAIL: " .. msg); end end
local function hero_at(mx, my) return u.ux == mx + OX and u.uy == my + OY; end
local function key(k) nh.pushkey(k); nh.doturn(true); end
local function boulder_at(mx, my)
   local o = obj.at(mx + OX, my + OY);
   while (o ~= nil and not o:isnull()) do
      if (o:totable().otyp_name == "boulder") then return true; end
      o = o:next(true);
   end
   return false;
end

-- Map (map-relative). Gadget origin N = (4,3). Rows/cols match §3.2 shifted by (+4,+3).
--   col: 0123456789
local MAP = [[
          
    . .   
    . .   
    ...   
  ...     
    .     
    ....  
          
         .]];
-- all rows 10 wide; ' ' = stone (no 'T' glyph: that would be a tree).
-- row 0 blank (stone); (4,1) P in, (6,1) P out; T=(4,2); N=(4,3) W; (5,3),(6,3);
-- back segment (2,4),(3,4); Q=(4,4); (4,5); C=(4,6); forward (5,6),(6,6),(7,6).
-- (9,8) = sentinel pit cell, isolated by stone.

local function build(start)
   des.reset_level();
   des.level_flags("noflip", "sokoban", "noteleport");
   des.level_init({ style = "solidfill", fg = " ", lit = true });
   des.map({ x = OX, y = OY, map = MAP });
   des.object("boulder", 4, 3);                -- W on N
   des.trap("pit", 9, 8);                       -- sentinel (never reachable)
   des.teleport_region({ region = { start[1] + OX, start[2] + OY, start[1] + OX, start[2] + OY },
                         region_islev = true, dir = "both" });
   des.finalize_level();
   u.clear_inventory();
   u.giveobj(obj.new("cursed loadstone"));
   check(hero_at(start[1], start[2]), "hero not placed");
end

build({4, 1});
key("j");                                  -- to T (4,2)
check(hero_at(4, 2), "did not reach T");
key("n");                                  -- FORBIDDEN: diagonal T->(5,3), corners N(boulder),(5,2)(stone)
check(hero_at(4, 2), "diagonal bypass of N succeeded");
key("j");                                  -- push W from N into Q
check(hero_at(4, 3), "push N->Q failed");
check(boulder_at(4, 4) and not boulder_at(4, 3), "W not on Q");
key("l");                                  -- continue the branch
check(hero_at(5, 3), "branch continuation blocked");

-- trapped segment: back to N, push W further down to (4,5), then to corner C (4,6)
key("h"); key("j");
check(hero_at(4, 4) and boulder_at(4, 5), "second push failed");
key("h");                                  -- into back segment (allowed, dead end)
check(hero_at(3, 4), "back segment not entered");
key("l"); key("j");                        -- Q, then push W into C
check(hero_at(4, 5) and boulder_at(4, 6), "W not at corner C");
key("j");                                  -- FORBIDDEN: push W out of C downward (stone)
check(hero_at(4, 5), "W pushed beyond corner C");
key("n");                                  -- FORBIDDEN: diagonal (4,5)->(5,6), corners C(W),(5,5)(stone)
check(hero_at(4, 5), "forward part reached around blocked corner");
check(boulder_at(4, 6), "W left corner C");

nh.pline("on_close: all checks passed");
