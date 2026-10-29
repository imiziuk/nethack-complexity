-- exp_coin_zone3.lua -- witness W11b for proofs/exptime-feasibility.md sec. 3 (teleport coin), generated variant.
-- W11b positive control: Z = {C,A,T,B} (extra free cell C); expect landings in {A,B,C}, nothing outside Z.
-- Run with tools/witness_driver_exp.py (it answers the WIZARD-MODE-ONLY getpos prompt of scrolltele() with '.',
-- i.e. picks the hero's own cell T, a trap cell => teleok() false => "Sorry..." => safe_teleds(): exactly the
-- non-wizard code path, teleport.c:870-924). The old witness_driver.py does not answer that prompt.
-- Map-relative coords (OX, OY). Z = coin zone; T = tele trap; A, B = the two landing cells; E = entry cell.
local BOOTS = true;          -- wear cursed fumble boots
local ZONE = "zone3";          -- "coin": Z = {A,T,B}; "zone3": Z = {C,A,T,B}; "none": no exclude
local REPS = 40;            -- re-entries in this run

nh.debug_flags({ mongen = false, hunger = false });
local OX, OY = 1, 0;
local T  = {8, 1};
local A  = {7, 1};
local B  = {9, 1};
local E  = {8, 2};
local C  = {6, 1};            -- free cell next to A: outside Z except in the zone3 variant
local S0 = {2, 3};            -- hero start (Rev. 3: single-cell start region, branch stair in sealed pocket)
local MAP = [[
--------------------
|...............|-.-
|......-.-......|---
|...............|   
-----------------   ]];
-- pocket '.' at (18,1) is sealed by walls (8 neighbours), >= 3 columns from the board.

local function at(c) return u.ux == c[1] + OX and u.uy == c[2] + OY; end
local function check(cond, msg) if (not cond) then error("HARNESS " .. msg); end end

local function zone_rect()
   if (ZONE == "coin") then return { 7 + OX, 1 + OY, 9 + OX, 1 + OY }; end
   if (ZONE == "zone3") then return { 6 + OX, 1 + OY, 9 + OX, 1 + OY }; end   -- adds free cell C=(6,1)
   return nil;
end

local function build_once()
   des.reset_level();
   des.level_flags("noflip", "sokoban", "hardfloor", "solidify", "premapped");   -- NO "noteleport"
   des.level_init({ style = "solidfill", fg = " ", lit = true });
   des.map({ x = OX, y = OY, map = MAP });
   des.region(selection.area(0, 0, 19, 4), "lit");
   des.trap({ type = "teleport", x = T[1], y = T[2], seen = true });
   des.levregion({ region = { 18 + OX, 1 + OY, 18 + OX, 1 + OY }, region_islev = true, type = "branch" });
   local z = zone_rect();
   if (z ~= nil) then
      des.teleport_region({ region = { S0[1] + OX, S0[2] + OY, S0[1] + OX, S0[2] + OY }, region_islev = true,
                            exclude = z, exclude_islev = true, dir = "both" });
   else
      des.teleport_region({ region = { S0[1] + OX, S0[2] + OY, S0[1] + OX, S0[2] + OY }, region_islev = true,
                            dir = "both" });
   end
   des.finalize_level();
   u.clear_inventory();
   u.giveobj(obj.new("cursed loadstone"));
   if (BOOTS) then u.giveobj(obj.new("cursed fumble boots")); end
   return at(S0);
end

local built = false;
for attempt = 1, 10 do
   if (build_once()) then built = true; break; end
end
check(built, "hero not on start cell after 10 builds");

-- one move key. Fumbling's nomul(-2) (and the unmul at its end) clears the canned key queue (hack.c nomul ->
-- cmdq_clear), so a key pushed while the hero is helpless is dropped: re-push until the hero has moved (<= 8 tries;
-- a dropped key cannot also be executed later, so there is no double move). Returns true iff the hero moved.
local function step(k)
   local x0, y0 = u.ux, u.uy;
   for tries = 1, 8 do
      nh.pushkey(k); nh.doturn(true);
      if (u.ux ~= x0 or u.uy ~= y0) then return true; end
   end
   return false;
end

local function find_boots()
   local o = u.inventory;
   while (o ~= nil and not o:isnull()) do
      local t = o:totable();
      if (t.otyp_name == "fumble boots") then return t; end
      o = o:next();
   end
   return nil;
end

local worn, cursed = 0, 0;
if (BOOTS) then
   local t = find_boots();
   check(t ~= nil, "no boots");
   local let = t.invlet;
   if (type(let) == "number") then let = string.char(let); end
   nh.pushkey("W" .. let); nh.doturn(true);
   t = find_boots();
   if (t.owornmask ~= 0) then worn = 1; end
   if (t.cursed ~= 0) then cursed = 1; end
   check(worn == 1, "boots not worn");
end
local tr = nh.gettrap(T[1] + OX, T[2] + OY);
local tseen = (tr ~= nil and tr.tseen) and 1 or 0;

-- walk to E: (2,3) -> (8,3) -> (8,2)
for i = 1, 6 do step("l"); end
step("k");
check(at(E), "did not reach entry E");

local cnt = { A = 0, B = 0, T = 0, C = 0, O = 0, X = 0 };
local seq, other = "", "";
local done = 0;
for r = 1, REPS do
   local moved = step("k");                     -- E -> T
   local c;
   if (not moved) then c = "X";                 -- never left E: harness problem, not a landing
   elseif (at(A)) then c = "A"; elseif (at(B)) then c = "B"; elseif (at(T)) then c = "T";
   elseif (at(C)) then c = "C"; else c = "O"; end
   cnt[c] = cnt[c] + 1; seq = seq .. c; done = r;
   if (c == "O" or c == "X") then other = other .. (u.ux - OX) .. "/" .. (u.uy - OY) .. ";"; break; end
   if (c == "A") then step("n"); elseif (c == "B") then step("b"); elseif (c == "T") then step("j");
   elseif (c == "C") then step("l"); step("n"); end
   if (not at(E)) then other = other .. "noreturn@" .. (u.ux - OX) .. "/" .. (u.uy - OY) .. ";"; break; end
end

nh.pline("RES:n=" .. done .. ",A=" .. cnt.A .. ",B=" .. cnt.B .. ",T=" .. cnt.T .. ",C=" .. cnt.C .. ",X=" .. cnt.X
         .. ",O=" .. cnt.O .. ",start=1,worn=" .. worn .. ",cursed=" .. cursed .. ",tseen=" .. tseen
         .. ",hp=" .. u.uhp .. "/" .. u.uhpmax .. ",moves=" .. u.moves);
nh.pline("SEQ:" .. seq);
if (other ~= "") then nh.pline("OTHER:" .. other); end
