# Downs & Vogel
*Converted from: Downs & Vogel.pdf*

---

## Page 1

COmpuh?rs c&-m. Engng. Vol. 17, No. 3, pp. 245-255, 1993

Printed in Great Britain

A PLANT-WIDE

INDUSTRIAL

PROCESS

PROBLEM

CONTROL

J. J. DOWNS and E. F. VOGEL

Eastman Chemical Company, Kingsport, T’N 37662, U.S.A.

0098-1354/93

86.00 + 0.00

Pcrgamon

Press Ltd

(Received

3 October

1991;Jinal revision received 1 I May

1992; received for publication

16 June 1992)

Abstrad-This

paper describes a model of an industrial chemical process for the purpose. of developing,

studying and evaluating process control technology. This process is well suited for a wide variety of

studies including both plant-wide control and multivariable control problems. It consists of a reactor/

separator/recycle arrangement involving two simultaneous gas-liquid

exothermic reactions of the

following form:

A(g) + C(g) + D(g) -P G(liq),

Product 1,

A(g) + C(g) + E(g) -

H(liq),

Product 2.

Two additional byproduct reactions also occur. The process has 12 valves available for manipulation and

41 measurements available for monitoring or control.

The process equipment, operating objectives, process control objectives and process disturbances are

described. A set of FORTRAN

subroutines which simulate the process are available upon request.

INTRODUCTION

For

several years we have heard the chemical

engineering process control academic community

express interest in having a realistic problem for

testing process control technology. We first heard

the topic discussed at the second Engineering Foun-

dation Conference on Chemical Process Control

meeting in 1981 (Denn, 1982). The topic was also

discussed at the first Engineering Foundation Confer-

ence on Chemical Process Control meeting in 1976

(Foss and Denn, 1976). Shell presented a test problem

at their process control workshop (Prett and Morari,

1986) and Ed Bristol discussed the characteristics of

a test problem in a recent paper (Bristol, 1987). Most

recently, AIChE initiated a session on the topic of

industrial-based test problems in which this problem

first appeared (Downs and Vogel, 1990).

As

the corporate

process

control

group

for

Eastman Chemical Company, we see a wide variety

of chemical processes. A few years ago we encoun-

tered a process which we believe is particularly well

suited for use as a test problem. Although we have

modified the components, kinetics, process and oper-

ating conditions to protect the proprietary nature of

the process, this test problem is based on an actual

industrial process (not a contrived problem). Bill

Luyben of Lehigh University and Charlie Moore of

The University of Tennessee looked at this probIem

and encouraged us to offer it for study. Both Bill

and Charlie teach courses and guide research in the

process control field.

We believe that this problem is well-suited for

studying process control technology and that it

is applicable to a wide variety of control issues.

The process model has been coded into a set of

FORTRAN

subroutines which describe the non-

linear relationships in the unit operations and the

material and energy balances.

This paper contains a description of the pro-

cess, the process control objectives, suggestions for

potential applications and details for using the model.

PROCESS

DESCRIPTION

The process produces two products from four

reactants. Also present are an inert and a byproduct

making a total of eight components: A, B, C, D, E,

F, G, and H. The reactions are:

A(g) + C(g) + D(g) -

G(liq),

Product 1,

A(g) + C(g) + E(g) -

H(liq),

Product 2,

A(g) + E(g) -

F(liq),

Byproduct,

3D(g) -

2F(liq),

Byproduct.

All the reactions are irreversible and exothermic.

The reaction rates are a function of temperature

through an Arrhenius expression. The reaction to

produce G has a higher activation energy resulting in

more sensitivity to temperature. Also, the reactions

are approximately first-order with respect to the

reactant concentrations.

245

---

## Page 2

246

J. J. DOWNS and E. F. VOGEL

---

## Page 3

Plant-wide process control problem

247

The process has five major unit operations: the

reactor, the product condenser, a vapor-liquid sep-

arator, a recycle compressor and a product stripper.

Figure 1 shows a diagram of the process. Table 1

provides the base case steady-state heat and material

balance data for the process and Table 2 lists the

component physical properties.

The gaseous reactants are fad to the reactor where

they react to form liquid products. The gas phase reac-

tions are catalyzed by a nonvolatile catalyst dissolved

in the liquid phase. The reactor has an internal

cooling bundle for removing the heat of reaction. The

vapor-liquid separator. Noncondensed components

recycle back through a centrifugal compressor to

the reactor feed. Condensed components move to

a product stripping column to remove remaining

reactants by stripping with feed stream number 4.

Products G and H exit the stripper base and are

separated in a downstream refining section which

is not included in this problem. The inert and

byproduct are primarily purged from the system as

a vapor from the vapor-liquid separator.

There are six modes of process operation at three

different G/H mass ratios (stream 11):

Mode

G/H mass ratio

Producti

rate (f&ream 11)

1

XI/50

7038 kg h-‘G

and 7038 kg h-‘H

(base case)

2

1 o/90

1408 kg h-r G and 12,669 kg h-’

H

3

90/10

lO,OOOkgh-‘G

and 1111 kgh-‘H

4

50/50

maximum production rate

5

10190

maximum production rate

6

go/10

maximum production rate

products leave the reactor as vapors along with the

Mode

1 is the base case. The product mix is

unreacted feeds. The catalyst remains in the reactor.

normally dictated by product demands. The plant

The reactor product stream passes through a cooler

productionrate is set by market demand or capacity

for condensing the products and from there to a

limitations.

Table 1. Heat and material

balance data (Mode I. basecase~

Rocwastrcamdata

stnem name

stream number

Molar

Bow (kgmol h- ‘)

Mass flow (kgh-')

Temperatwe("C)

Mole fractions A

:

D

:

G

H

stteamname

Strcamnumbcr

Molar flow (kgmolh-')

Mass Bow (kgh-')

Temperaturc(‘C)

Molefractions A

B

C

D

F

G

H

Temperaturc("C)

p===(~gawe

Heat duty (kW)

Liquid volume (m')

A feed

Dfeed

1

2

11.2

114.5

22.4

3664.0

45.0

45.0

Efeed

938.0

450Q.3

45.0

Cfeed

4

417.5

6419.4

45.0

StrpOvhd

46z7

897916

65.7

o.QQQQo

O.OOOOO

O.OOOOO

0.48500

0.00010

0.ooo10

O.OtIOOO

O.OOH)o

O.OtXlOO

O.OOOOO

O.OOlXO

0.51000

O.OOOOO

O.QQQ90

O.OOOOO

O.OOOOO

O.WOOil

O.OOOLW

0.99990

O.ooooO

O.OOOOO

O.OWOO

0.00010

O.OOOOO

O.OOOOO

O.WOOO

O.OOOOO

O.CWOO

O.WOOO

O.ooooO

OXtOOOO

O.ooooO

0.43263

x:4=

0.00116

0.07256

0.00885

0.01964

0.00808

Reactor product

Recycle

purge

Separation

liquid

Roduct

7

8

9

10

I1

1476.0

1201.5

15.1

259.5

211.3

48.015.4

30,840.O

386.5

16.788.9

14,288.6

120.4

102.9

80.1

80.1

65.7

0.27164

0.32958

0.32958

O.OOOW

0.00479

0.11393

0.13823

0.13823

O.CKKIOO

O.OOOOQ

0.19763

0.23978

0.23978

O.OOOOO

0.01008

0.01075

0.01257

0.01257

0.00222

O.ooOl8

0.17722

0.18579

0.18579

0.13704

0.00836

0.02159

0.02263

0.02263

0.01669

O.OOOQ9

0.12302

0.04844

0.04844

0.47269

0.53724

0.08423

0.02299

0.02299

0.37136

0.43828

RCZSt0r

120.4

2705.0

-6468.7

16.55

?z?Y

2633.7

-

4.88

-2140.6

-

StlippCr

65.7

3102.2

1430.0

4.43

utmues

Rcactorcoolingwater

flow

(m'h-I)

93.37

Condemwcooli~gwatcr

5?w(m'h-')

49.37

Reactor f&d

6

lSQO.8

48015.4

86.1

0.32188

0.08893

0.26383

0.06882

0.18776

0.01657

0.03561

0.01659

stripper

stream Uow(kgh-')

230.31

---

## Page 4

248

J. J. DOWNS and E. F. VOGE.L

Table 2. Component physical properties (at 100°C)

Liquid

Liquid heat

Vapor heat

Heat of

Mokcular

density

capacity

capacity

vaporization

Component

weight

(kg m?

(kJ kg-’

“C-‘)

(kJ kg-’

“C-l)

W kg-‘)

A

2.0

B

25.4

C

28.0

D

32.0

E

46.0

F

48.0

G

62.0

l-l

76.0

-

-

14.6

-

2.04

-

-

-

1.05

-

299

7.66

1.85

202

365

4.17

I .a7

372

328

4.45

2.02

372

612

2.55

0.712

523

617

2.45

0.628

486

Vapor pressure (Antoine equation):

P = exp[A + B/(T + C)]

P = pressure (Pa)

T = temperature (“C)

component

Constant A

Constant B

constant c

D

20.81

- 1444.0

259

E

21.24

-2t14.0

266

F

21.24

-2144.0

266

G

21.32

-2748.0

233

H

22.10

-3318.0

250

Vapor pressure

parameters are not listed for components A, B and C because they are effectively

CONTROL

OBJECllVEs

Process

constraints

The process has 41 measurements and 12 manipu-

lated variables as listed in Tables 3-5. A prerequisite

for most studies on this problem is a process control

strategy for operating the plant. The control objec-

tives for this process are typical for a chemical process:

1.

2.

3.

4.

5.

Maintain process variables at desired values.

Keep

process

operating

conditions

within

equipment constraints.

Table 6 lists the specific operational constraints

that the control system should respect. These con-

straints are primarily for equipment protection. The

high and low shutdown limits are part of the process

interlock strategy and are used to shutdown the

process in the event the process conditions get out of

hand.

Product

variability

Minimize

variability

of

product

rate

and

product quality during disturbances (stream 11).

Minimize

movement

of valves which affect

other processes (in this case the gas feeds as

described below).

Recover quickly and smoothly from disturb-

ances, production rate changes or product mix

changes.

The variability of the product stream is important

with regard to the downstream distillation system

which refines products G and H. Flowrate changes

of stream 11 greater than f 5%

with significant

frequency content in the range &I6 h-’

are particu-

larly harmful. In addition, composition variability

greater than +5 mol% G with significant frequency

content in the range 6-10 h-l are equally harmful.

Table 3. Process maniuulated variables

Variable name

Variable

number

D feed flow @tram

2)

XMV

(1)

E feed flow (stream 3)

XMV r2,

A feed flow (stream 1)

XMV

i3j

A and C feed flow (stream 4)

XMV (4)

Compressor recycle valve

XMV (5)

Purpc valve (stream 9)

XMV (6)

Swarator oat liauid flow ~stream 10)

S&per

Ii&id p;oduct So& (stream ‘I 1)

XMV (7)

XMV (8)

Stripper steam valve

XMV (9)

Reactor cooling water flow

XMV

(10)

Condenser cooling water flow

XMV

(1 I)

Aaitator sueed

XMV (12)

Base

case

value (%.)

63.053

53.980

24.644

61.302

22.210

40.064

38.100

46.534

47.446

41.106

18.114

50.000

Low

limit

0

0 x

0

0

0

0

0

:

150

High

limit

5811

8354

1.017

15.25

100

100

65.71

49.10

100

227. I

272.6

.

250

Units

kgh-’

kgh-’

kscmh

kscmh

%

%

m’h-’

m’ h-’

%

m’h-’

m’ h-’

mm

Each of the manipulated variables is speoifibd by setting the corresponding XMV variable to a value between 0 and 100.

The base case values are the initial values of the XMV variables. The ranges of all the XMV variables are O-100.

The low limits shown here are the actual or-s

variable values which correspond to XMV ci> = 0.0. Likewise_ the

high limits shown here are the actual p&s

variable values which correspond to XMV

(i)‘= 100.0.

The user can manipulate the XMV

variables outside the O-100 limits. However, within the function evaluator

(TEFUNC).

the XMV vector is copied to another vector which has hard constraints of 0 and 100. Thw. if an XMV

variable goes beyond the O-100 limits, its effect is constrained to 0 or 100, but the XMV variable value is not changed.

---

## Page 5

Variabie

uatne

Plant-wide

pnaccs2z control problem

Table 4. Continuous

process mcasurcrnents

Variabk

ti-

number

value

Units

249

A feed (stream

1)

XMEAS

(I)

D feed (st-

2)

XMEAS

(2)

E feexl ~strcam 3)

XMEAS

(3)

A and C feed (stream 4)

XMBAS

(4)

Recycle flow (St-

8)

XMEAS

(5)

Reactor

f&d rate (stream 6)

XMBAS

(6)

Reactor

pressure

XMEAS

(7)

Reactor

level

XMEAS

(8)

Reactor

anperature

XMBAS

(9)

Purge rate (stream 9)

XMEAS

(IO)

Product

separator

temperature

XMEAS

(11)

Product

separator

level

XMEAS

(12)

Product

separator

pressure

XMEAS

(13)

Product

separator

underflow

(stream

10)

XMBAS

(14)

stripper

level

XMEAS

(15)

stripper

pressure

XMEAS

(16)

Stripper underflow

(stream

11)

XMEAS

(17)

stripper

temperature

XMBAS

(18)

strippx

steam dew

XMEAS

(19)

Compressor

work

XMEAS

(20)

Reactor

coolinn water outlet ten-merature

XMEAS

(21)

separator cooling water outlet te~peratnre

XMEAS

i22j

77.297

0.25052

3664.0

4509.3

9.3477

26.902

42.339

2705.0

75.000

120.40

0.33712

80.109

50.000

2633.7

25.160

50.000

3102.2

22.949

65.731

230.31

341.43

94.599

Table 5. Sanmkd

ur-8

tneasurernents

k-

&aus=

%

“C

kscmb

‘C

%

k-

&au=

In’ h-1

%

kPa gauge

m3lI-’

“C

kg h-’

kW

“C

Reactor

feed analysis (stream 6)

Variable

component

number

A

XMEAS

(23)

B

XMEAS

(24)

C

XMEAS

(25)

E”

XMEAS

(26)

XMEAS

(27)

F

XMEAS

(28)

Base case

value

32.188

8.8933

26.383

6.8820

18.776

1.6567

Units

m01%

IIIOl%

mol%

llIOl%

lllOl%

mol%

Sampling

froqnency = 0.1 h

Dead

time-O.lh

Purge gas analysis (stream 9)

Variable

Component

number

A

XMEAS

(29)

:

XMEAS

(30)

XMEAS

(31)

D

XMEAS

(32)

E

XMEAS

(33)

F

XMEAS

(34)

HG

XMEAS

(35)

XMEAS

(36)

Product

analysis (stream

11)

Variable

Component

number

:

XMEAS

(37)

XMEAS

(38)

XMEAS

(39)

XMEAS

(40)

m-

vahlc

32.958

13.823

23.978

1.2565

18.579

2.2633

4.8436

2.2986

m-

value

0.01787

0.83570

0.09858

53.724

Units

XllOl%

m0l%

m0l%

lTlOl%

UlOl%

Inot%

lllOl%

IllOl%

Units

UlOl%

lllOl%

mol%

mol%

Sampling

fquency

- 0.1 h

Dead time-o.1

b

Sampling

fquency

- 0.25 h

Dead

time = 0.25 h

H

XMEAS

(41 j

43.828

mol%

The

analyzer

sampling frequency is how often the analyzer takes a sample of the stnam. The dead

time is the time between when a sampk

is taken and when the analysis is complete. For an

analyzer

with a sampling

frequency

of 0.1 h and a dead time of 0.1 h, a new measurement

is

available

every 0.1 h and the measurement

is 0.1 h old.

Table 6. Process operating

oonstraints

Normal

oneratimz timits

Shut down limits

Process variabk

Reactor

prcss”rc

Reactor

level

Reactor

temperature

Product

separator

kvel

stripper

base level

Low limit

IlOllC

(1 l?z$)

IkOlltZ

30%

(3.3 In’)

30%

High limit

2895 kPa

100%

(21.3 In’)

150°C

100%

(9.0 m’)

100%

Low limit

High limit

IIOPC

3ooO kPa

2.0 Ina

24.0 m3

POIU?

175°C

1.Olll-l

12.0 m3

l.0m3

8.0 m’

(3.5 aI?)

(6.6 m’)

---

## Page 6

J. J. Downs and E. F. VOGEL

Table 7. Setpoint changes for the base case

Process variable

Production rate change

Product mix change

Reactor operating pressure change

Magnitude

-15%

Make a step change to the variable(s) used to set the process production rate so

that the product flow leaving the stripper column base changes from 14,228

to 12,094 kg h-’

MG/5OH

to 4OG/6OH

Make a step change to the variable uwd to ensure correct product composition

so that the product production rates of G and H change from 7038 kg h-’ G

to 5630kgh-‘G

and from 7038kgh-‘H

to 8446kgh-‘H

-60 kPa

Make a step change so that the reactor operating pressure changes from 2705

to 2645 kPa

Purse sa.9 composition of

component

B change

Step

+2%

Make a step change so that the composition of component B in the gas purge

changes from 13.82 to 15.82%

Similar setpoint changes can also be made with the other operating modes.

To reali

the full effect of these setpoint changes, we suggest a simulation time of 24-48 h.

Control strategies should attempt to minimize this

or high-frequency ringing or chatter is undesirable for

type of variability on stream 11.

any of the manipulated variables.

Feed flow uariability

Dynamic performance

measure

The four feed streams are products of other pro-

duction facilities within the plant complex. Significant

holdup is available for feed stream 3, component E.

However, less holdup is available for feed streams 1

and 2, components A and D, and very little holdup

is available for feed stream 4, components A and C.

For those components which have little holdup,

changes in their feed flowrates to this process are

product demand changes to the processes producing

those components. As a result, flow variability of

three of the four feed streams is of concern, particu-

larly for stream 4. It is desired first to minimize flow

variability having frequency content in the range

12-80 h-’

for stream 4. For feed stream 1 and 2,

the A and D feeds, they should be protected from

variability having frequency content in the range

g-16 h-‘.

Finally, variability in the feed rate of E is

not of major concern. However, excessive movement

We have provided no mathematical measure for

evaluating the “performance”

of the many ways

to control this process. Although the dynamic per-

formance objectives have been described in the

sections above, we felt that the tradeoffs among the

possible control strategies and techniques involve

much more than a mathematical expression. Issues

such as tolerance to measurement failure or drift,

understandability by the plant operators, hardware

implementation considerations, maintenance, etc.

make a mathematical evaluation of control strategies

difficult.

Dynamic performance

comparisons

The testing and evaluation of various process

control technologies can be done with the setpoint

changes listed in Table 7 or the load changes listed

in Table 8. These setpoint and load disturbances

Table 8. Process disturbances

Variable number

IDV (1)

IDV 12)

IDV i3j

IDV (4)

IDV (5)

IDV (6)

IDV (7)

IDV (8)

IDV (9)

IDV (10)

IDV (I 1)

IDV (12)

IDV (13)

Process variable

A/C feed ratio, B composition constant (stream 4)

B comoosition. A/C ratio constant f&ream 41

- D feed’tcdpcrature (stream i,

Reactor cooling water inlet temperature

Condenser c4mting water inIet temperature

A feed loss (stream I)

C header pressure losereduced

availability (stream 4)

A, B, C feed composition (stream 4)

D feed temperature (stream 2)

C feed temperature (stream 4)

Reactor cooling water inlet temperature

Condenser cooling water inlet temperature

Reaction kinetics

Type

step

step

step

step

SkP

SkP

S=P

Random variation

Random variation

Random variation

Random variation

Random variation

Slow drift

IDV ii4j

Reactor cooling water valve

Sticking

IDV (15)

Condenser cooling water valve

Sticking

IDV (16)

Unknown

Unknown

IDV (17)

Unknown

Unknown

IDV (18)

Unknown

Unknown

IDV (19)

Unknown

Unknown

IDV (20)

Unknown

Unknown

Disturbances 14-20 should be used in conjunction with another disturbance from this table or a setpoinc change.

To realize the full ef&zt of these disturbances, we sumt

a simulation time of 24-48 h.

---

## Page 7

Plant-wide process control problem

251

represent a set of tests that can be used to compare

and contrast alternative approaches to operating and

automatically controlling this process. Each disturb-

ance illustrates a different aspect of operating the

process. We encourage users to try all the disturb-

ances and to try them at the different modes of

process operation.

To provide the common basis needed for the

purpose of publishing and comparing results, we

suggest disturbing the process at the base case

(Mode

1) with the four setpoint changes listed in

Table 7 and the following four load disturbances

from Table 8:

IDV( 1)

Step change

IDV(4)

Step change

IDV(8)

Random variation

IDV( 12), IDV( 15)

Simultaneous random

variation and sticking valve.

A qualitative comparison of the time responses of

at least the following process variables is desired:

A feed flowrate (stream I), D feed flowrate (stream 2),

E feed flowrate (stream 3), C feed flowrate (stream 4),

product flowrate (stream 1 I), product compositions

(stream 11) and reactor pressure.

PROCRSS

OPTIMIZATION

The

process has more manipulated variables than

necessary for controlling inventories and product

quality making optimization feasible. An objective

function based on operating costs is listed in Table 9.

Operating costs for this process are primarily deter-

mined by the loss of raw materials. Raw materials are

lost in the purge gas, the product stream and by

means of the two side reactions. Economic costs for

the process are determined by summing the costs of

the raw materials and the products leaving in the

purge stream, the costs of the raw materials leaving

in the product stream, and using an assigned cost to

the amount of F formed. Costs of the compressor

work and steam to the stripping column are also

included. Component values and a sample costs

calculation for the base case are listed in Table 9.

POTENTIAL

APPLICATIONS

This problem can be used for studying a wide

variety of topics:

1. Plant-wide cm&o1 strategy design-There

are

many control strategies that can be used to

control this plant. Steady-state analysis tools

such as RGA can be used to screen possible

Table 9. Proc.ss

opa-ating costs

component

Cost (S kgmol- ’ )

A

2.206

C

6.177

D

22.06

E

14.56

F

17.89

G

30.44

H

22.94

OpmtImgcoEta*tthebMccaee:

Purge losses:

Componmt

A

C

D

F

D

H

Lossm in the product:

Component

D

E

F

Comprrssor costs: SO.0536 (kW-h)-’

Stripper steam costs: SO.0318 kg-’

Mole fraction

Molar costs

0.32958

2.206

0.23978

6.177

0.01257

22.06

0.18579

14.56

0.02263

17.89

0.04844

30.44

0.02299

22.94

Costa per kgmol of purge

Mole fraction

Molar cost.9

0.00018

22.06

0.00836

14.56

0.00099

17.89

Costs per kgmol of product

0.7271

1.481 I

0.2773

2.7051

0.4049

I .4745

0.5274

7.5973

0.0040

0.1217

0.0177

0.1434

(purge

costs)(purge

rate)

+ (product stnzam costs)(product rate)

+ (compressor costs)(compmssor work) + (steam costs)(stcam rate) = total costs

S

7.5973-

kgmol h-’

kgmol 44.79r0.3371

kscmb + 0.1434-

9.21 kgmol h-’

~~22.95m’h-’

+ 0.0536&(341.4kW)+0.0318+0.3kgb-I)=

170.6Sh-’

---

## Page 8

252

J. J. DOWNS

and E. F. VOGEL

2.

3.

4.

5.

6.

7.

8.

schemes. Dynamic simulation can then be used

to test the performance of the schemes with the

disturbances listed in Tables 7 and 8. Control

strategies can be designed to reject disturbances

for all six modes of operation given in the

section titled “Process Description”.

Multivariable contro&Many

of the process

measurements respond to many of the manipu-

lated variables. Consequently, multivariable con-

trol may be beneficial for reducing interaction.

Optimisation-Both

steady-state and dynamic

optimization problems may be studied. Deter-

mine the optimum operating conditions for the

six modes of operation. Table 9 provides an

objective function.

Predictive controLThe

application of predic-

tive control

techniques containing

identifi-

cation, constraint handling and optimization

can be evaluated.

Estimation/adaptive

control-Variation

in pro-

duction rate and product mix may cause the

process dynamics to change sufEciently to merit

on-line controller adaptation.

Nonlinear control--The

reaction and vapor-

liquid equilibrium equations are quite nonlinear

and control may benefit from a nonlinear

approach to the problem.

Process diagnostics-Expert

systems and fault

diagnostics can be tested to evaluate their per-

formance and reaction to new or unknown

conditions.

EducatIo~This

problem could be used as

a study in process control courses to illustrate

the concepts of control strategy design, con-

troller tuning, control loop troubleshooting and

applications of advanaced control.

This list is intended to generate ideas for some of the

possible applications of this test problem. No doubt

there are other possible topics for study as well.

MODEL

DEBCRIPTION

We chose to present the test problem in the form

of FORTRAN

subroutines, hoping that this form

would be the easiest to use for the most people and

promote widespread use.

Below is a list of points that may be useful in using

the model:

The vapors all behave as ideal gases.

The vapor-liquid equilibrium follows Raoult’s

Law with the vapor pressure calculated using the

Antoine equation.

l Modeling

the process presented a

tradeoff

between rigor and model stiffness due to the gas

phase dynamics during pressure change. In

developing the process model, a compromise

was made to ensure realistic behavior for the

dynamics of primary interest while not having

the system become too stiff. The model is suiB-

ciently rigorous to capture the important pro-

cess dynamics. We did not include fast dynamics

such as transmitter lags. A linear eigenvalue

analysis at the base case was used to find the

fastest mode of the system. The largest negative

eigenvalue is 1968 h-l for a time constant of

about 1.8 s. The step size used in the sample

program (TEMAIN,

discussed below) is 1 s and

was sufficient for integration stability.

USE OF THE MODEL

SUBROUTINES

All the vessels are well mixed and contain no

The model consists of 10 FORTRAN

subroutines:

The list of manipulated variables, Table 3,

includes some variables listed as thousand stan-

dard cubic meters per hour (kscmh), kilograms

per hour (kg h-r), or as cubic meters per hour

(m3 h-l),

and some variables listed as valve

position (%).

For those manipulated variables

listed as kscmh, kg h-l, or m3 h-l, the flowrate

is not a function of upstream or downstream

pressure. For those manipulated variables listed

as valve position (%), the flowrate is a function

of pressure. If a constant flowrate in the pres-

ence of pressure changes is desired, a flow

controller should be included. The text at the

bottom of Table 3 discusses how constraints on

the manipulated variables are handled.

The reactor is agitated. Agitation speed only

affects the heat transfer coefficient.

The recycle gas compressor is a centrifugal type

and has internal surge protection by means of

a mechanical bypass arrangement. The relation

between flow through the compressor

and

inlet-outlet pressure difference follows a typical

centrifugal compressor curve.

l All

process measurements include Gaussian

noise with standard deviation typical of the

measurement type.

l Table 6 lists the process constraints, both normal

operating limits and process shutdown limits.

The process should be operated within the

normal operating limits. If the process exceeds

the shutdown limits, it will automatically be shut

down as described in the section below.

l The model is not intended for simulating process

start-up and shutdown procedures.

distributed parameters.

TEFUNC,

TEINIT

and TESUBl,

. _ . , TESUBI.

---

## Page 9

Plant-wide process control problem

253

To run the model, the user must provide a main

to return the simulation to the base-case, initial

program, an integration algorithm, control algor-

condition.

ithms and output routines. A simple example main

program, TEMAIN,

is included with the subroutines

TEINIT

is called as follows:

and illustrates their use as well as all of the elements

CALL TEINIT(NN,

YY, YP).

needed to run the model. TEMAIN

linked with the

10 subroutines forms a sample executable program.

TEINIT’s

inputs are

TEFUNC

NN = No. of variables (states) to integrate.

(Subroutine argument list.)

TEFUNC

is the function evaluator to be called

from an integration subroutine. It calculates current

TEINIT’s

outputs are

process variable measurements and derivatives from

the current states provided from the integrator.

W

= Vector containing the initial values of the

states.

The user must provide the integration algorithm.

TEFUNC

is called as follows:

CALL TEFUNCQI-N,

TIME, YY, YP).

TEFUNC’s

inputs are:

(Subroutine argument list.)

YP = Vector containing the initial derivatives of

the states.

(Subroutine argument list.)

Utility subroutines

NN = Number of variables (states) to integrate.

There are 50 states for simulating the

There

are

8 utility subroutines, TESUBl,

. . . ,

TESUBS. They are all called by TEFUNC,

and the

process.

(Subroutine argument list.)

user need not call any of them.

TIME = Current time in hours. Updated by the

Constraints

integrator.

(Subroutine argument list.)

TEFUNC

tests the process variables which have

W

= Vector containing the current values of

shutdown constraints as listed in Table 6. If any

the states. Calculated by the integrator.

variable violates a shutdown constraint, the process

(Subroutine argument list.)

will automatically be shut down. More specifically,

XMV = Vector of manipulated variables.

TEFUNC

sets all the derivatives to zero, because it

(Common block: PV.)

is invalid to operate the process outside these limits.

IDV = Vector of disturbance flags.

Restarting the process requires calling TEINIT which

(Common block: DVEC.)

resets the process to the base case condition and

enables TEFUNC

to again calculate derivatives.

TEFUNC’s

outputs are:

User’s interface

YP = Vector containing the current derivatives

of the states.

The user’s “interface” to the model is through two

(Subroutine argument list.)

common blocks as explained below.

XMEAS

= Vector of process variable measurements.

COMMON/PV/XMEAS(41),

XMV(12):

XMEAS

(Common block: PV.)

is the vector of process measurements which are

calculated in TEFUNC

from the current states.

TEINIT

TEINIT is the initialization subroutine. It specifies

the initial values of the states (the variables that are

integrated) and the initial values of the manipulated

variables. It also specifies the values of variables that

are constant, such as physical properties. The values

of the states and manipulated variables as specified

by TEINIT correspond to the base-case, steady-state

operating condition (as shown in Tables 1, 3,4 and

5). TEINIT

calls TEFUNC

to calculate the initial

process measurement values. After calling TEINIT,

the values of the derivatives will all be close to

zero. TEINIT

should be called when first starting

the simulation

program

and anytime the user wishes

The measurements contained in this vector are

listed in Tables 4 and 5. Elements of XMEAS

are

REAL*8

variables.

XMV

is the vector of manipulated variables

which the user specifies either as constant values or

as outputs of control algorithms. The variables

contained in this vector are documented in Table

3. When specifying values for the manipulated

variables through XMV,

the range for all of the

manipulated variables is O-100. The manipulated

variables are then scaled by TEFUNC

according to

the ranges listed on Table 3. Table 3 also discusses

how

constraints on

the XMVs

are handled.

Elements of XMV

are REAL*8

variables.

---

## Page 10

254

J. J. Dowrrs and E. F. Voon

COMMON/DVEC/IDV(ZO)t

IDV is a vector of

disturbance flags which the user sets as either on (1)

or off (0). The disturbances corresponding to the

elements of IDV are listed in Table 8. Setting an

element to 1 turns on the disturbance. Setting an

element to 0 turns off the disturbance. The user

may turn any of the disturbances on or off at any

time separately or simultaneously and they are

applicable to all six modes of process operation.

The variables changed for the disturbance return to

their base case values upon setting the disturbance

flag back to 0. Elements of IDV are INTEGER*4

variables.

TEMAIN

Figure 2 shows a flowchart for TEMAIN.

The

process is initialized with a call to TEINIT. Disturb-

ance flags, manipulated variables to be held constant

(different from their initial values), and setpoints

are specified. The remainder of TEMAIN

is the

simulation loop. The loop begins by executing the

discrete control algorithms which update their ma-

nipulated variables. Next, desired measurements and

manipulated variables for the current time step are

saved for later printing or plotting. Last, the integra-

tor is called to integrate the process ahead to the next

time step. TEMAIN

uses a simple Euler integrator

for example.

Saving process operating conditions

The operating conditions may be saved for purpose

of restoring the simulation to a condition other than

the base case by writing the state vector (YY) and the

manipulated variable vector (XMV)

to a file. After

reading the YY and XMV variables, the user must set

the variable TIME to zero and then call TEFUNC

to

update all the other measurements. Setting TIME to

zero, causes the sampled process measurements to be

re-initialized correctly.

Controllers

The user may implement controllers as either dis-

crete or continuous algorithms. The simulation loop

in TEMAIN

illustrates the implementation of dis-

crete controllers. Comment statements in TEINIT

and TEFUNC

show where additional states needed

for continuous controllers may be appended to the

process model and included in the integration.

Steaay -state comergence

In addition to integrating TEFUNC

to perform

dynamic simulation, TEFUNC

may also be used

to converge the test problem to new steady-states.

A

convergence

algorithm

such

as

Newton

or

Broyden can be used to drive the values of the

Fig. 2. Flowchart of TEMAJN.

derivatives returned from TEFUNC

to zero. The user

will need to append any controllers or design specifi-

cations to the states and derivatives of TEFUNC.

When converging to steady-state, call TEFUNC

with

TIME = 0. Only when TIME = 0 is there no noise on

the measurements.

Program

code

The subroutines were developed

DEC

so

that

be compiled on

by

intention,

We prefer

that

on process control, as

opposed to modeling

of meaningful comparisons,

we do

to

encourage modification of the model.

Example

simulation

Figure 3 shows the open-loop dynamic responses

for eight process measurements to a step change in

the reactor cooling water flow rate. XMV(l0)

=

41.106 m3 h-l

was changed

to XMV(l0)

= 38.00

m3 h-’ and held constant throughout the simulation.

All other manipulated variables were constant at

their base case values (no controllers in automatic).

No other disturbances were present (all IDVs = 0),

other than the normal measurement noise. This

simulation was performed with an Euler integrator

---

## Page 11

Plant-wide process control problem

255

77.001

Reac

L$vel..

72.00

o.boo

o.ioo

o.ioo

0.300

o.boo

o.ioo

0.200

Fig. 3. Open-loop responses for step change in reactor cooling water flow.

(constant step size of 1 s) and the response data was

has only a few unit operations, it is much more

plotted every sixth step.

complex than it appears on frrst examination. We

OBTAINING THE SOURCE CODE

The

FORTRAN

source code

is available by

request from either author. We can send it by elec-

tronic mail (Internet or BITNET)

or on 34” floppy

(IBM PC or Macintosh format). We recommend that

you obtain a copy directly from us. By requesting the

program from us, we will know who has a copy and

we can notify users of any future modifications.

hope that this problem will be useful in the develop-

ment of the process control field. We are also inter-

ested in hearing about applications of the problem.

RJWERENCES

Bristol E. H., Benchmark/theme models for the control

society. Unpublished (1987).

SUMMARY

Denn M.

M.,

Chemical Process Control 2, Proc. of the

Engineering Foundation ConJ (T. F. Edgar and D. E.

Seborg, Eds). Engineering Foundation (1982).

Downs J. J. and E. F. Voge4, A plant-wide industrial process

control problem. Paper 24a, AKitE

1990 Annual Meeting,

Chicago.

IL (1990).

The chemical process model presented here is a

challenging problem for a wide variety of process

control technology studies. Even though this process

Foss A. S. and M. M. Denn, Chemical process control.

AIChE Symp. Ser. 72, 232 (1976).

Prett D. M. and M. Morari, Shell Process Control Work-

shop. Butterworth Publishers, Stoneham, MA (1986).

---

