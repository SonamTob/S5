# iGEM fluorescein serial dilution - OT-2, 8-channel P300 (rows A-H)
# Building-block commands only.

from opentrons import protocol_api

metadata = {
    "apiLevel": "2.19",
    "protocolName": "TeamX iGEM Fluorescein Serial Dilution",
    "author": "Team X",
}

###Settings (check these in the lab) 
DRY_RUN = False                      # True = no liquid, tips go back in the rack

RESERVOIR = "4ti0131_12_reservoir_21000ul"  
PLATE = "costar3370flatbottomtransparent_96_wellplate_200ul"
TIPS = "opentrons_96_tiprack_300ul"
MOUNT = "left"                       # side the 8-channel pipette is on

DYE_VOL = 200      # uL fluorescein into column 1
PBS_VOL = 100      # uL PBS into columns 2-12
VOL = 100          # uL moved column to column
MIX_VOL = 120      # uL
MIX_REPS = 3
TOUCH_SPEED = 20   # mm/s for touch tip (Opentrons default is 60; lower = gentler)

def run(protocol: protocol_api.ProtocolContext):

    # Labware: plate slot 1, reservoir slot 2, tips slot 4
    plate = protocol.load_labware(PLATE, 1)
    reservoir = protocol.load_labware(RESERVOIR, 2)
    tiprack = protocol.load_labware(TIPS, 4)

    p300 = protocol.load_instrument("p300_multi_gen2", MOUNT, tip_racks=[tiprack])
    p300.flow_rate.aspirate = 94
    p300.flow_rate.dispense = 94
    p300.flow_rate.blow_out = 150

    pbs = reservoir["A1"]          # >= 12 mL 1X PBS
    dye = reservoir["A2"]          # >= 3 mL 10 uM fluorescein
    waste = reservoir["A12"]       # empty, liquid waste
    cols = plate.rows()[0]         # A1..A12 (8-channel does the whole column A-H)

    def done_with_tips():     # drop or return tips depending on DRY_RUN
        p300.return_tip() if DRY_RUN else p300.drop_tip()


    def take(vol, well, height):    
        # slow aspirate, short pause so liquid settles, slow exit so no drops cling
        p300.aspirate(vol, well.bottom(height), rate=0.5)
        protocol.delay(seconds=0.5)

    def mix(well):  ## Although, Opentrons have a built-in mix command, we set separate aspirate and dispense rates to avoid splashing and bubbles. 
        # slow up, fast down to mix; last stroke slow so the tip drains
        for i in range(MIX_REPS):
            p300.aspirate(MIX_VOL, well.bottom(1), rate=0.5)
            p300.dispense(MIX_VOL, well.bottom(3),
                          rate=0.25 if i == MIX_REPS - 1 else 1.5, push_out=0)

    # 1. 100 uL PBS into columns 2-12 (one tip set: wells are empty)
    p300.pick_up_tip()
    for col in cols[1:]:
        take(PBS_VOL, pbs, 1.5)
        p300.dispense(PBS_VOL, col.bottom(2))
        p300.blow_out(col.top(-2))                  # empty the tip fully
    done_with_tips()

    # 2. 200 uL fluorescein into column 1 (new tips, kept for the dilution)
    p300.pick_up_tip()
    p300.aspirate(DYE_VOL, dye.bottom(1.5), rate=0.5)          # pre-wet tip once
    p300.dispense(DYE_VOL, dye.bottom(3), rate=0.5, push_out=0)
    take(DYE_VOL, dye, 1.5)
    p300.dispense(DYE_VOL, cols[0].bottom(2), rate=0.5)
    p300.blow_out(cols[0].top(-2))

    # 3. Serial dilution: 100 uL column 1 -> 2 -> ... -> 11, mix 3x each time
    for i in range(10):
        take(VOL, cols[i], 1)
        p300.touch_tip(cols[i], v_offset=-2, radius=0.8, speed=TOUCH_SPEED)  # gentle wipe
        p300.dispense(VOL, cols[i + 1].bottom(1.5), rate=0.5, push_out=0)  # below surface
        mix(cols[i + 1])

    # 4. Remove the final 100 uL from column 11 to waste (column 12 untouched)
    take(VOL, cols[10], 1)
    p300.dispense(VOL, waste.top(-2))
    p300.blow_out(waste.top(-2))
    done_with_tips()
