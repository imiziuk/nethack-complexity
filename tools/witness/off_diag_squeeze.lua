-- off_diag_squeeze.lua -- witness W3 for proofs/hu-off.md (Lemma S, case M1: no corner cutting)
-- STATUS: written, NOT RUN. Harness and coordinate conventions: see off_push_orth.lua header.
-- Source claim: src/src/hack.c:1153-1171 with bad_rock (939-945: Sokoban && boulder) and
-- cant_squeeze_thru case 3 (953-978): a diagonal step whose two corner squares both hold
-- boulders is refused under the sokoban flag; with one free corner it is allowed.
-- Control run without the flag shows the same step succeeds (boulders are not bad_rock then).

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;

local function check(cond, msg)
   if (not cond) then
      error("W3 FAIL: " .. msg);
   end
end

local function boulder_at(ax, ay)
   local o = obj.at(ax, ay);
   while (o ~= nil and not o:isnull()) do
      if (o:totable().otyp_name == "boulder") then
         return true;
      end
      o = o:next(true);
   end
   return false;
end

local function hero_at(mx, my)
   return u.ux == mx + OX and u.uy == my + OY;
end

local function key(k)
   nh.pushkey(k);
   nh.doturn(true);
end

local function build_once(map, boulders, start, soko, heavy)
   des.reset_level();
   if (soko) then
      des.level_flags("noflip", "sokoban", "noteleport", "hardfloor", "solidify");
   else
      des.level_flags("noflip", "noteleport", "hardfloor", "solidify");
   end
   des.level_init({ style = "solidfill", fg = " ", lit = true });
   des.map({ x = OX, y = OY, map = map });
   for _, b in ipairs(boulders) do
      des.object("boulder", b[1], b[2]);
   end
   des.teleport_region({ region = { start[1] + OX, start[2] + OY, start[1] + OX, start[2] + OY },
                         region_islev = true, dir = "both" });
   des.finalize_level();
   for _, v in pairs(nh.stairways()) do
      des.terrain(v.x, v.y, ".");  -- DL1 branch stair from finalize (review-2 N2), as in src/test/testmove.lua
   end
   u.clear_inventory();
   if (heavy) then
      u.giveobj(obj.new("cursed loadstone"));
   end
   return hero_at(start[1], start[2]);
end

-- harness retry: finalize places the DL1 branch stair at random; if it lands on the 1-cell start
-- region the hero is not placed ("Couldn't place lregion"). Setup randomness only, not gadget behaviour.
local function build(map, boulders, start, soko, heavy)
   for attempt = 1, 10 do
      if (build_once(map, boulders, start, soko, heavy)) then return; end
   end
   check(false, "hero not placed on the start square after 10 builds");
end

local ROOM = [[
-------
|.....|
|.....|
|.....|
-------]];

-- (a) Sokoban, both corners are boulders: hero (2,3), boulders (3,3) and (2,2), target (3,2) free
build(ROOM, { {3,3}, {2,2} }, {2,3}, true, true);
key("u");
check(hero_at(2, 3), "Sokoban: hero squeezed diagonally between two boulders");
check(boulder_at(3 + OX, 3 + OY) and boulder_at(2 + OX, 2 + OY), "Sokoban: a corner boulder moved");

-- (b) Sokoban, only one corner is a boulder: the diagonal step is legal (= two orthogonal steps)
build(ROOM, { {3,3} }, {2,3}, true, true);
key("u");
check(hero_at(3, 2), "Sokoban: diagonal step with a free corner was refused");
check(boulder_at(3 + OX, 3 + OY), "Sokoban: corner boulder moved during a plain step");

-- (c) control without the flag: boulders are not bad_rock, the squeeze of (a) succeeds
build(ROOM, { {3,3}, {2,2} }, {2,3}, false, true);
key("u");
check(hero_at(3, 2), "control: hero could not cut the corner outside Sokoban");

nh.pline("W3 off_diag_squeeze: all checks passed");
