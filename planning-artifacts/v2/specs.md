A. Item Sheet Management
Goal: Centralize and standardize documentation for all lab items (consumables and non-consumables).
User Stories:
As a Quality Team member, I want to
Create and edit item sheets so that all lab items are documented with technical details and compliance information.

Fields for Non-Consumables (Instruments/Kits):
Name (required)
Files
Tags (e.g., "Hazardous", "Priority")
Note
Fields for Consumables (Reagents):
Name (required)
Unit (mL, g, etc.) (required)
Quantity (required, e.g., "10 mL")
Files
Storage Conditions (e.g., "-20°C", "Room Temperature"
Tags (e.g., "Hazardous", "Priority")
Note

As a user, I want to:
Search and filter item sheets by name, supplier, type, or tags so I can quickly find and select items for batch creation.
As a user, I want to:
Add or remove tags from item sheets to categorize and organize items effectively.

B. Inventory Managementlink

Goal: Track batches (internal or received) with full traceability, supporting multiple items per batch.

User Stories:link

As a Lab Technician, I want to:
Declare a reception (internal or received) so I can manage stock efficiently.
Reception Workflow:
Click "Receive" button.Fill in metadata:
External Lot Number (mandatory, e.g., supplier’s lot ID)stored in tagInternal Lot Number (auto-generated or manual)stored in tagCreation Date (auto-filled)Supplier (required) Add one or more items from the Item Sheet:
Search and select items (consumables or non-consumables).Create a new item if that does not existFor each item, specify:
Quantity (unity)Expiration Date (optional for non-consumables, required for consumables)Location (required)Barcode (auto-generated or scanned)Custom Label (optional)Tags (e.g., "Hazardous", "Priority") => hérité Notes (free text)Attachments (e.g., Certificate of Analysis)Serial Number (optional) -> non consumable. 1 serial number = 1 item unitSave Batch: System validates inputs and creates the batch with all associated items.Key Rules:
A batch can contain multiple items (e.g., a kit with reagents, buffers, and instruments).Each item in the batch must have its own quantity and expiry date (if applicable).The system auto-calculates the total batch quantity based on item quantities.

As user, I want to:
Edit batch details (e.g., update item quantities, locations, or tags) to correct errors or reflect changes.

As a user, I want to:
Perform actions on batches (e.g., transformations, splits, moves) to manage lab workflows effectively.
Supported Actions:
Receive (log new stock)
Move (change location of an item)
Relabel (update labels)
Retag (update tags)
Discard (remove expired/contaminated batches)
Transform
Consume (reduce quantity of a specific item)
Split (divide a batch into sub-items)
Combine (merge multiple batches)
Dilute/Concentrate (adjust sample properties)
As a user, I want to:
Scan barcodes to quickly retrieve batch or item information (optional).

D. Activities (Transformations/Events)link

Goal: Log all actions performed on batches/samples for full traceability.

User Stories:link

As a Lab Technician, I want to:
Log transformations (e.g., splits, mixes, dilutions) to track sample history and ensure reproducibility. I also want to track the instrument I use

Add row aboveAdd row belowDelete rowAdd column to leftAdd column to rightDelete column ActionDescriptionExampleReceiveLog a new batch into inventory.Batch A = 500 mL (new)ConsumeReduce the quantity of a specific item in a batch.Before: A = 500 mL → After: A = 480 mL (consumed 20 mL)SplitDivide a batch into sub-batches.A (100 µL) → A1 (30 µL) + A2 (30 µL) + A (40 µL)MoveChange the location of a batch or item.A (Fridge A) → A (Fridge B)CombineMerge multiple batches or items into a new batch.A (10 mL) + B (5 mL) → M1 (15 mL)DiscardRemove a batch or item (e.g., expired/contaminated).Batch A discarded (reason: contamination)DiluteAdjust the concentration of a sample by adding solvent.A (10 mL, 1M) → A (20 mL, 0.5M)ConcentrateReduce the volume of a sample to increase concentration.A (20 mL) → A (10 mL)RelabelUpdate batch/sample labels or tags.Add tag "Priority" to Batch A



  - Transformation rules : are mentioned at the end of the document.

         For each activity we have to mention: 

List of Input itemsList of Output itemsList of InstrumentsDatetime [par defaut date du jour]OperatorDescription

5. Hierarchical Display of Batches and Items
Display batches and items in a single hierarchical table:

6. Automatic Item Sheet Creation
If a new item is created by combining existing items (e.g., A + B → C), and C does not have an item sheet:
Show a popup asking the user to create an item sheet for C.
7. Units of Measurement
Celles qu'on a déjà + ce qui manque )
Catégorie
Unité
Exemple d’usage concret
Volume
L
Solvants, milieux (ex: 1 L de PBS)
mL
Tampons, cultures (ex: 50 mL de LB)
µL (uL)
Enzymes, ADN/ARN (ex: 2 µL de Taq)
Volume (à ajouter)
nL
Microfluidique / distributeurs HT (ex: 50 nL par puits)
Masse
kg
Poudres en vrac (ex: 1 kg NaCl)
g
Réactifs solides (ex: 250 g agarose)
mg
Standards, petites quantités (ex: 5 mg primer)
Masse (à ajouter)
µg (ug)
ADN/ARN/protéines (ex: 10 µg d’ARN total)
ng
ADN faible quantité (ex: 20 ng d’ADN plasmidique)
Length
m
Tubing, films (ex: 2 m de tubing)
cm
Membranes/feuilles (ex: 10 cm de membrane)
mm
Diamètre, joints (ex: filtre 25 mm)
Length (à ajouter)
µm (um)
Pore size filtre/membrane (ex: filtre 0.22 µm)
Count (units)
pcs
Consommables (ex: 96 pcs tips)
Count (à ajouter)
cells
Culture cellulaire (ex: 1×10⁶ cells)
copies
qPCR/NGS (ex: 2×10⁵ copies)
CFU
Microbio (ex: 100 CFU)
Catégorie
Unité
Exemple d’usage concret
Amount (à ajouter)
mol
Chimie / solutions mères (ex: 0.1 mol)
mmol
Préparation solutions (ex: 5 mmol MgCl₂)
µmol
Oligos, standards (ex: 20 µmol d’amorce)
nmol
Oligos (ex: 5 nmol d’ADN)
pmol
qPCR/primers (ex: 10 pmol par réaction)
Catégorie
Unité
Exemple d’usage concret
Concentration (mass/vol)
masse par volume
ng/µL
ADN/ARN (ex: ADN = 50 ng/µL)
µg/mL
Protéines/ARN (ex: protéine = 200 µg/mL)
mg/mL
Anticorps / protéines (ex: Ab = 2 mg/mL)
g/L
Milieux / chimie (ex: glucose 10 g/L)
Concentration (molaire)
nombre de moles par volume
M
Solutions stock (ex: Tris 1 M)
mM
Buffers/ions (ex: MgCl₂ 10 mM)
µM
Oligos/ligands (ex: primer 10 µM)
nM
Sondes (ex: probe 250 nM)
Concentration (activité enzyme)
la “puissance” enzymatique par volume.
U/µL
Enzymes (ex: Taq 5 U/µL)
U/mL
Enzymes en vrac (ex: DNase 1000 U/mL)
Concentration (count/vol)
la “puissance” enzymatique par volume.
cells/mL
Comptage cellules (ex: 3×10⁵ cells/mL)
copies/µL
qPCR (ex: 1×10⁴ copies/µL) estimé par qPCR

Transformation rules
1. Consume
Objective
Reduce the available quantity of a specific input item without creating a new scientific output entity.
Inputs
Exactly 1 input entity required
Allowed input :
 item ID
Mandatory input fields:
Input Entity ID
Available Quantity (already stored in the system)
Quantity to Consume
Unit
description
List of Instrument
datatime
operator
Outputs
The system updates the remaining quantity of the input entity
Business Rules
Consumed quantity must be greater than 0
Consumed quantity must be less than or equal to available quantity
Unit must match the stocked unit or follow allowed conversion rules
If remaining quantity = 0, entity status may become:
Exhausted
Traceability Rules
Store before quantity
Store consumed quantity
Store after quantity
Store operator, datetime, and reason
Keep reference to the source entity
2. Split
Objective
Divide one input entity into multiple child entities.
Inputs
Exactly 1 input entity required
Allowed input:
item ID
Mandatory input fields:
Input Entity ID
Available Quantity (already stored in the system)
Unit
description 
List of Instrument
 datatime 
operator
Outputs
At least 2 output entities required
Each output must have:
Output ID
Quantity
Unit
Location
Label 
                  expiration date
                   note
Business Rules
Sum of output quantities must be less than or equal to input quantity
Remaining quantity handling must be configurable:
either full split: input is closed and fully replaced by outputs
or partial split: input remains open with reduced quantity
All outputs must keep the same material identity as the parent unless explicitly allowed otherwise
Units must be compatible
Traceability Rules
Each output must store a parent reference to the original input
The split activity must preserve genealogy:
Parent → Child 1, Child 2, Child 3

IDs must be unique
3. Combine
Objective
Merge several input entities into one new output entity.
Inputs
Minimum 2 input entities required
Allowed input types:
 items id (1....n)
Mandatory per input:
Input Entity ID
Quantity contributed
Unit
description 
List of Instrument
 datatime 
operator
Outputs
Minimum 1  output entity 
Output fields:
Output ID
Output Quantity
Output Unit
Output Location
Output Label 
date of expiration 
note
Business Rules
At least 2 inputs required
Output quantity must equal the sum of valid input quantities, unless loss is explicitly declared
If loss is allowed, system must record:
theoretical quantity
actual quantity
quantity loss
reason

Inputs may be:
fully consumed
partially consumed

Combine must not be allowed across incompatible units without conversion
4. Dilute
Objective
Decrease the concentration of an input entity by adding a diluent.
Inputs
Minimum 2 inputs required:
1 target entity to dilute1 diluent entity
Allowed target :
items ID
Allowed diluent :
item ID
Mandatory fields:
item ID
Target volume 
Initial concentration
Diluent item ID
Diluent added volume 
Final target volume
Final target concentration or dilution factor
description 
List of Instrument 
datatime 
operator

Outputs
New derived outputcreate a new diluted child entity
Mandatory output fields:
Output ID
Output quantity
Output unit
Output concentration
Output location
date of expiraton
Business Rules
Diluent input is required
Final concentration must be lower than initial concentration
Final volume must be greater than initial volume
Dilution factor must be calculable and stored
the diluent consumed quantity must be deducted
Input and diluent units must be compatible
Traceability Rules
Output must reference:
source entity
diluent entity
dilution factor
initial and final concentration

5. Concentrate
Objective
Increase the concentration of an input entity by reducing solvent volume or applying a concentration process.
Inputs
Exactly 1 item ID is  required
Mandatory fields:
Input Entity ID
Initial volume
Initial concentration
Final  volume
Final concentration
Concentration method (evaporation , Ultrafiltration, Lyophilization, Precipitation, Centrifugal concentration)=> optional
description
 List of Instrument
 datatime 
operator
Outputs
- Create a new concentrated derived entity
Mandatory output fields:
Output ID
Output quantity
Output unit
Output concentration
Output location
date of expiration
Business Rules
Final concentration must be higher than initial concentration
Final volume must be lower than initial volume, unless method defines another mechanism
Losses must be recorded when applicable
Concentration method may be required from a controlled list (optiona)
