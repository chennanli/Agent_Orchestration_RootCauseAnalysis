# TEP McAvoy
*Converted from: TEP McAvoy.pdf*

---

## Page 1

Compurers c/rem. Enene Vol. 18. No. 5. pp. W-413.

lYY4

Copyright 0

lYY4 Elscvicr Scicncc Ltd

Printed in Great Britain. All rights rcscrvcd

owx-1354/94

$6.w+o.tx,

BASE CONTROL

FOR THE TENNESSEE

EASTMAN

PROBLEM

T. J. McAvov

and N. YE

Department

of Chemical

Engineering,

University

of Maryland,

College

Park,

MD 20742,

U.S.A.

(Received

4 November

1992; final

revision

received 23 August

1993; received for

publication

9 September

1993)

Abstract-This

paper

presents

an approach

to configure

a basic

PID

control

system

for the recently

published

Tennessee

Eastman

testbed

process

control

problem.

A multiloop

single-input-single-output

control

architecture

is used.

The control

design

approach

involves

using a combination

of steady-state

screening

tools,

followed

by dynamic

simulation

of the most

promising

candidates.

The

steady-state

tools employed

are the relative

gain, Niederlinski index. and disturbance analysis. The resulting

control

system

satisfies

all of the specifications required for the design. The final PID system is appropriate for

adding on top of it an advanced strategy for online optimization and it can be used as a basis for assessing

the benefits

of advanced

control.

INTRODUCTION

Recently,

several companies

have published

testbed

problems

for use in evaluating

advanced

process

control

approaches.

The

first such

problem

was

published

by Shell in 1986 (Prett and Morari,

1986).

Since then Amoco

(McFarlane

ef al.,

1993), Johnson

Wax

(Chylla

and

Haase,

1993)

and

Tennessee

Eastman

(Downs

and Vogel,

1993) have published

problems.

This

paper

focuses

on

the

Tennessee

Eastman

problem

which involves

a process with 41

measurements

and

12

manipulated

variables.

A

detailed

description

of this process,

including typical

disturbances

and baseline

operating

conditions,

is

given

in Downs

and

Vogel

(1993).

The

process

involves

the

production

of two

products,

G and

H,

from

four

reactants:

A,

C, D,

and

E.

In addition

there

are

two

side reactions

that occur and an inert

B essentially

all of which enters with one of the feed

streams.

The authors

of the Tennessee

Eastman

problem

point

out

that

it is an appropriate

testbed

for a

number of topics. These include:

plant-wide

control

strategy design,

multivariable

control,

optimization,

predictive

control,

estimation/adaptive

control,

nonlinear

control,

process

diagnostics

and educa-

tion.

The

purpose

of

this paper

is to present

a

systematic

approach

to

developing

a plant-wide

decentralized

control

system design.

This design is

based on multiple single-input-single-output

(SISO)

control

loops.

The

resulting

design

can form

the

basis

upon which an advanced

control

scheme,

such

as predictive

control,

can be built. In addition

it can

also be used to compare

the advantages

of employ-

ing other more advanced

control

approaches.

The

systematic

approach

presented

consists

of

four broad stages, based upon loop speed. In Stage 1

inner cascade

loops are closed.

In Stage 2 the basic

decentralized

PID system is designed.

Stage 2 design

involves

all loops except

those associated

with the

process

analyzer

and product

rate.

Stage

3 design

involves closing the analyzer and product rate loops.

Lastly,

at Stage

4 higher

level

controls,

such

as

model predictive

control and/or

optimization

can be

added.

As one proceeds

from Stages l-3,

the speed

of the loops involved

decreases.

The flow loops are

the fastest,

followed

by the level, temperature

and

pressure

loops.

The product

composition

and pro-

duct Row loops are the slowest. Thus. the plant-wide

strategy decomposes

the problem

into stages based

upon relative loop speed. The majority

of the paper

is concerned

with the Stage 2 design. Before discuss-

ing Stage 2 design, an overview of the various design

stages is given.

OVERVIEW

OF CONTROL

SYSTEM DESIGN APPROACH

The

plant

control

system

can

be

designed

in

several stages.

An overview

of these stages is given

below followed

by a detailed discussion for Stage 2.

Stage

I

At stage 1 inner

cascade

loops

are closed,

based

upon experience.

As can be seen in Fig. 1 there are

eight flow and two temperature

cascade

loops that

can be closed.

The flow loops involve the four feed

streams,

the purge

stream,

the stripper bottoms,

the

separator

bottoms

and the stripper steam flow. The

two temperature

cascades involve the condenser

and

reactor cooling streams.

Once these loops are closed

CACE 15:5-B

3x3

---

## Page 2

3x4

T. J. McAvov

and N. YE

*

--

5:

4

4

t

:

JO

0

E

-- “d

4

N

0 6;: -- a

n

---

## Page 3

Base control

for the Tennessee

Eastman

problem

Tahlc 1. Process disturhanccs

385

Variahlc

number

Process variahlc

Type

IDV(I)

IDV(2)

lDV(3)

I DV(4)

IDV(5)

IDV(h)

IDV(7)

IDV(X)

lDV(9)

lDV( IO)

IDV(II)

lDV(l2)

IDV( 13)

IDV( 14)

IDV(l5)

A/C feed ratio. B composition cnnstant (Stream 4)

B compusitinn.

A/C

ratio constant (Stream 4)

D feed tcmpcraturc

(Stream 2)

Reactor cooling water inlet tcmpcraturc

Condcnscr

ccxlling water inlet tcmpcraturc

A feed loss (Stream

I)

C hcadcr prcssurc loss-rcduccd

availability

(Stream 4)

A. B, C feed composition (Strum

4)

D feed tcmpcraturc

(Strum

2)

C feed tcmpcraturc

(Stream 4)

Reactor cooling water inlet

Cundcnscr

cooling water inlet tempcraturc

Reaction kinetics

Reactor cooling water valve

Condcnscr cooling water valve

step

step

step

step

step

step

step

Random variation

Random variation

Random variation

Random variation

Random variation

Slow drift

Sticking

Sticking

and the controllers

tuned,

the flow and temperature

indicators,

FT and TI, in Fig. 1 can be replaced

with

controllers,

FC and TC.

The manipulated

variables

then become

the setpoints

of the flow and tempera-

ture

loops.

The

speed

controller

on

the

reactor

agitator,

labeled

SC,

is in effect

identical

to the

setpoints

of the inner flow and temperature

loops of

the cascades.

The closure

of the 10 cascades

elimi-

nates 10 of the 41 process

measurements.

One result of closing

the cascade

loops is that the

impact of several of the process disturbances.

shown

in Table

1, are decreased

significantly

since

they

enter

the

inner

loop

of the cascades.

These

dis-

turbances

involve

inlet cooling

water temperature,

IDV(4),

IDV(5).

IDV(ll)

and IDV(12),

the pres-

sure in the C feed

line,

IDV(7),

and the sticking

valves,

IDV(14)

and

IDV(l5).

Treatment

of dis-

turbances

is discussed

later in the paper.

Stage 2

To carry out the next level of control

design,

it is

assumed

that the plant must be operational

even if

the analyzer

is not functioning.

This assumption

is

important

since analyzers

are typically

less reliable

than the more common

temperature,

pressure,

flow

and level sensors.

In addition

the analyzer loops are

typically

slower.

Stage

3 design,

discussed

below,

involves

closing

the analyzer

loops.

If the 19 ana-

lyzer measurements

are eliminated,

then there are

41 - 10 - 19 = 12 potential

variables

to be controlled

at Stage

2. These

variables

are listed in Table

2.

There

are

also

12

manipulated

variables,

which

include

the 10 cascade

setpoints,

the agitator

speed

and the recycle valve around the compressor.

These

manipulated

variables

are also

listed

in Table

2.

Figure 2 illustrates

the 12 x 12 problem

that must be

addressed

at Stage 2. It should be emphasized

that it

may

not

be possible

or desirable

to close

all

12

loops.

The tools that are used here to address

this

problem

are:

the relative

gain (Bristol,

1966),

the

Niederlinski

Index (1971).

linear saturation

analysis,

nonlinear

disturbance

and

saturation

analysis

(Vogel

and Downs,

1991) and finally dynamic

simu-

lation

(Vogel

and

Downs,

1991).

Singular

value

decomposition

(Smith et al., 19X1) also yields useful

information

on this problem,

but it is not considered

here due to space limitations.

The approach

used is

discussed

in detail in the following

section.

Sfage 3

At Stage 3 it is assumed

that process levels,

flows,

temperatures

and pressures

are controlled

as the

result of the Stage

2 design.

Next,

one

needs

to

configure

the analyzer

loops.

To do so the process

chemistry

and the specifications

on production

rate

and product

mix

need

to be considered.

Product

mixes of 10/90,

50/W

and 90/10

for the G/H

ratio

need to be produced

and the product

flow needs to

be adjusted.

To develop

a control

strategy

for how

to make

these changes

it is convenient

to examine

simplified

overall

material

balances

for the plant.

Although

a relative gain analysis could be applied to

the simplified

material

balance

results,

an approach

based

on

material

balance

arguments

is

taken

below.

Both

approaches

lead to the same

conclu-

sions. After

stage 2 the plant can be viewed from an

overall perspective

as shown in Fig. 3. Although

the

Tahlc 2. Manipulated

and controlled

variahlcs

Manipulated

Cw~trollcd

A-feed sctp>int

D-feed sctpoint

E-feed sctpoint

C-feed sctpoint

Purge sctpoint

Product octpoint

Stripper steam fl0w sctpoint

Separator

lwttom How sctpwnt

Reactor cooling wutcr sctpoint

Condcnscr ccmling water sctp>int

C0mprcssor

rccyclc valve

Stirrer speed

Reactor lcvcl

Separator

lcvcl

Stripper bottom lcvcl

Reactor prcssurc

Reactor feed Row

Reactor tcmpcraturc

Comprcssw

pmvcr

Compressor exit How

Scp;lr;lt<w prc\sure

Separator

tcmpcrilturc

Stripper prcssurc

Stripper tcmpcraturc

---

## Page 4

386

T. J. McAvov

and N. YE

0 5:

.- -

v

__

Q_

: “p-

---

## Page 5

Base

control

for the Tennessee

Eastman problem

387

7

A+C+D

-

G

A+C+E

-

H

Temperatures,

Levels.

Pressures.

and Flows are under control

Fig

four feed

streams,

the product

stream

and the purge

stream

are shown,

some of these streams

may not be

available

for

manipulation

if they

are assigned

to

loops

during

Stage

2 design.

This

point

will

be

addressed

later on.

Since

the purge

stream

is small compared

to the

product

How,

it will

be neglected

in the simplified

material

balance.

Further,

only

the two

reactions

producing

the G and H products

will be considered.

The extent

of reaction

1 is taken

as e, and reaction

2

T&lc

3.

Simpliticd

~vcrall

material

halanccs

GIH=Il408

(kg/h)ll[lZ,hhY

(kg/h)1

IO/Y0

stream

Component

MOICS

Mass

Product

C-feed

A-feed

D-feed

E-teed

G

22.7(cl)

140X

H

166.7

(e2)

l2,WY

T<%ll

14.077

A

1x0. I

360.3

C

1X9.4

5303

Total

5663.3

A

Y-3

IX.6

D

22.7

736.7

E

166.7

766X.2

St rciml

G/H

=(703X

kg/h)/(703X

kg/h)

Component

MOICS

Product

C-feed

A-feed

D-feed

E-feed

G

113.4

(cl)

7(13X

ii

Y2.h

(62)

703X

‘I otill

14.076

A

lY)h

3Y2

C‘

2tl6. I

5770.X

Total

6162.X

A

IO. I

20.2

D

113.5

3532

E

Y2.h

425Y .h

G/H

= (12,hhY

k@h)/(

140X kg/h)

Yt)o/ III

stream

Crlmponcnt

Molt>

Mask

Product

C-feed

A-feed

D-feed

E-feed

G

204.3

(cl)

12569

H

IX.5

(c2)

140x

Total

14.077

A

21 l.Y

423.X

c

222.x

h23X.4

Total

hhh2.2

A

10.5,

21.x

D

204.3

h537.h

E

1X.5

x51

3

as ez_ Then,

from

reaction

I the

amount

of

G

produced

is e, and the amount

of D reacted

is also

e,. From

reaction

2 the amount

of H produced

is el

and

the

amount

of

E

reacted

is ez.

Since

C

is

required

in both

reactions

1 and 2, e, plus e2 moles

of

C

react

and

e,

plus

e7 moles

of

product

are

produced.

The

amount

of A that enters

with the C

feed

is calculated

from

the base case compositions

given

in (Downs

and Vogel,

1993). The

moles

of A

in the C feed

are equal

to (0.48YO.510)

x (e, + e2).

The

A feed

is assumed

to provide

the

additional

moles

of A so that a total of e, + e2 moles

of A enter

the system.

Table

3 shows

the results

of this simplified

mat-

erial

balance

for the three

product

mix conditions.

The

results

in Table

3 indicate

that to control

the

product

mix,

the relative

amounts

of D and E need

to be changed

substantially.

After

Stage

2 design

at

least one of these two manipulated

variables

must be

available

to control

the product

mix.

If both

the D

and E flows are available,

then changing

the product

mix is straightforward.

If only one flow is available.

then the other

must be used to control

an inventory

variable,

i.e. level or pressure.

so that it can respond

to changes

in the free

input

flow.

When

the free

variable

is changed,

then

the

inventory

would

be

affected

in such a way that the manipulated

variable

tied to it changes

to achieve

the desired

product

mix.

Further,

the

simplified

analysis

indicates

that

the

G/H

ratio

varies

directly

with

the D/E

ratio,

and

thus manipulation

of the D/E

ratio

to control

the

G/H

ratio

in the product

is suggested.

The results in

Table

3 also show

that for a fixed

production

rate,

the C feed

Row does

not change

appreciably

as the

product

mix changes.

This

result

can be expected

since

C is required

for

both

products.

In order

to

vary the production

rate, the best variable

to use is

the

product

rate

itself.

If product

rate

cannot

be

used because

it is required

for Stage 2 control,

then

---

## Page 6

388

T.J. McAvov

and N. YE

T&lc 4. Constraints

results

from

Stage

3: analysis

hascd on simpli-

manipulated

to control

the amount

of B in the plant.

lied material

balance

A disturbance

analysis can be used to decide

if the

I. Both the C feed

and

product

Row

cannot

bc

used

in Stage

2

ables

resulting

from

the Stage

3 analysis

are sum-

design

2. Both

the D feed

and E feed

cannot

hc used in Stage 2 design.

marized

in Table

4.

3. If the accumulation

of B is a prohlcm.

the purge sctpoint

needs

to hc used to control

the composition

of B.

Stage 4

At stage 4 higher level controls

are added

on top

of the basic plant control

system.

These

higher level

the C feed can be used. The D and E feeds are not

controls

include:

steady

state

control

(Piovoso,

appropriate

for production

rate control,

since they

lYY2),

steady state optimization

(Forbes

et al., 1992)

change

appreciably

with

product

mix

at a fixed

and model

predictive

control

(Cutler

and Ramaker,

production

rate. The A feed is too small for produc-

1979).

Stage 4 controls

are beyond

the scope of this

tion rate control,

and it does not change

enough

for

paper.

product

mix

control.

Thus,

after

Stage

2 design

either

the

product

flow

or the

C flow

should

be

DETAILED

DESCRIPTION

OF

STAGE

2 DESIGN

available

for production

rate control.

Also,

it may

be desirable

to ratio

feed

flow(s),

internal

flow(s)

There

are

a number

of

steps

that

need

to be

and compressor

power

to the setpoint

of product

carried

out to complete

the Stage

2 design.

These

flow.

include:

Step

1 close the level loops;

Step 2 assess

The last point to consider

is the elimination

of the

interaction,

stability,

and saturation

problems;

Step

inert component

B. This component

enters with the

3 carry out a steady-state

disturbance

analysis;

and

C

feed

and

it essentially

goes

out

in the

purge

Step 4 tune and test candidate

control

systems

via

stream.

Since

B is a gas,

its accumulation

could

dynamic

simulation.

Each

step is discussed

separ-

cause

problems,

including

a rise in pressure.

If B

ately below.

purge must be used to control

the amount

of B in the

Step 1

system.

The

constraints

on the manipulated

vari-

Of all the controlled

variables in a plant, levels are

accumulates,

then

the

purge

stream

needs

to be

probably

the most important.

One cannot

afford

to

AFeed

D Feed

C Feed

Purge

steam

Rea Cl

SepaCl

RLXy

Agit

setpt

Sctpt

setpt

setpt

setpt

Setpt

setpt

Valve

Speed

Fked

Rea

-8.2062

-0.0030

3.2054

-7.6820

0.0009

-0.6652

0.2346

-0.0360

0.1291

Y( 1)

_

Rea

Temp

6.4830

0.0022

1.6619

0.8968

0.0005

1.1106

0.0281

0.0141

-0.2149

Y( 21

Rea

Pres

-3103.2488

-0.2796

287.0500

-965.7145

0.0477

-31.4794

11.9680

7.7756

6.1135

Y( 3)

&pa

Temp

67.8248

0.0109

-7.4203

21.0053

-0.0020

2.2502

0.2853

-0.1954

-0.4359

Y( 4)

Stri

Temp

46.0956

0.0095

-6.4259

20.1120

0.0368

1.8663

0.4130

-0.0380

-0.3615

Y( 5)

&CY

Flow

-11.2025

-0.0028

1.6500

-7.0837

0.0004

-0.6510

0.2640

-0.0187

0.1256

Y( 6)

camp

POW.%-

126.7784

-0.0159

13.2484

-27.4335

0.0090

-4.5126

2.5222

2.9658

0.8732

Y( 7)

Sep.3

PIW3

-3053.8689

-0.2744

281.1390

-948.6965

0.0465

-30.9414

11.8017

8.5438

6.0093

YI 8)

stri

PmS

-3377.3005

-0.3080

319.9876

-1059.6489

0.0561

-34.4602

12.8932

3.4986

6.6962

Y( 9)

Fig. 4

---

## Page 7

Base

control

for the Tennessee Eastman problem

have

a vessel

overflow

or run dry.

Further,

level

loops

must be closed

in order

to calculate

steady-

state gains.

Otherwise,

step changes

in manipulated

variables

produce

ramp-like

responses

which

result

in valve saturation

or constraint

violation.

At Stage

2 there are 3 levels that need to be controlled:

the

separator

level,

the stripper

bottoms

level and the

reactor

level.

The

logical

choice

for the separator

level is its bottoms

flow

setpoint.

For the stripper

bottoms

level,

either

the product

flow setpoint,

or

the steam flow setpoint

can be used. Since there are

constraints

on

how

fast

the product

flow

can be

manipulated,

if it is used

then

a loosley

tuned

averaging

level

loop

should

be employed.

For the

reactor

level, tight control

is required

and the cool-

ing water

setpoint

or the E feed setpoint

are simple

possibilities.

Ricker

et ul.

(1993)

discuss

a more

complicated

level control

strategy

in which

recycle

rate

and

condenser

cooling

are

used.

This

more

complex

strategy

may have an advantage

for plant

operation

over the complete

10/90, 50/50 and 90/10

product

mix.

Using

the E feed

for

level

control

means

that

the E feed

can only

be set at some

percentage

of its maximum,

e.g.

90%,

otherwise

389

level control

will be lost due to valve saturation.

For

the IO/90 G/H

case limiting

the E feed to 90%

will

also limit the maximum

production

rate.

This

paper

addresses

control

around

the 50/50

setpoint

and the various

control

objectives

given in

Downs

and

Vogel

(1993)

as tests

for

a control

system

design.

As

discussed

in Downs

and Vogel

(1993),

feed streams

A and D have constraints

on

their rate of change

and thus they can be ruled out,

since

fast level

control

cannot

be achieved

using

them.

Once

the level

loops

are assigned,

steady-

state gains

for

the resulting

9 x 9 process

can be

calculated

using

the procedure

given

in McAvoy

(1983).

Small

positive

and

negative

changes

are

made in the manipulated

variables

and the resulting

changes

in the controlled

variables

are averaged.

Since

there

are four

possible

level

configurations,

there

are four

9 x 9 systems

that need

to be ana-

lyzed. Detailed

results for one of these systems

are

presented

below

along with a summary

of results for

the other

three cases. The specific case considered

involves

using the E feed to control reactor level and

the product

flow to control

the stripper

level.

The

gain matrix for this system is shown

in Fig. 4.

Table 5

Scheme 1

A-feed

Row

Steam flow

Reactor cooling

Comp. rccyclc

sctpoint

sctpoint

setpoint

valve

Reactor tcmpcraturc

-0.036

-O.OlY

1.030

0.025

Reactor D~CSSUW

0.921

0.015

-Il.045

0. I ox

Strip tckpcrature

0.012

1.007

-0.023

0.004

Comp power

0. If12

-0.003

0.037

0.863

Schcmc 2

A-feed

flow

Steam flow

Reactor cooling

Condcnscr

cooling

Comp rccyclc

sctpoint

setpoint

sctpomt

sctpoint

valve

Reactor tcmpcraturc

Reactor prcssurc

Strip tempcraturc

Comp power

Feed reactor

Schcmc 3

A-feed

flow

sctpoint

Steam Row

setpoint

Reactor cooling

Condcnscr

cooling

Comp rccyclc

sctpoint

sctpoint

vaivc

Reactor tcmpcraturc

Reactor prcssurc

Strip tcmpcraturc

Comp power

Separator

tcmpcraturc

Schcmc 4

Reactor tcmpcraturc

Reactor prcssurc

Strip tcmpcraturc

Comp powcr

Rccyclc Row

A-feed

How

sctpoint

-0.014

0.962

0.007

0. 105)

-0.tJt?5

Steam fbw

sctpoint

-0.034

0.020

I.039

-0.w7

-0.020

Rcector cooling

Condcnscr

cooling

Camp recycle

sctpoint

sctpoint

valve

0.989

(I.(&2

-0.utl3

-0.ll4Y

-0. II11

0. I67

-0.021

-0.02x

IJ.0tP

0.040

O.OXh

0.771

t1.041

0.981

o.oh2

---

## Page 8

390

T. J. McAvov

and N. YE

must be controlled results in a smaller number of

RGA cases to be examined, but it does not change

the basic methodology. Also, it is possible that if too

many variables are specified as definitely having to

be controlled, one may not get to a solution. In this

case the specification on variables that definitely

have to be controlled has to be relaxed. By specify-

ing that 4 variables must be controlled, the number

of RGAs that must be considered is relatively small.

There are 3 6 x 6 cases, 18 5 x 5 cases and 15 4 x 4

cases, giving a total of 36 cases. In addition to using

the Niederlinski Index to rule out unstable pairings,

physical arguments can be used as well. For exam-

ple, one would not pair the D-feed flow with the

stripper temperature due to how far apart physically

these variables are. Similarly, the use of the very

small purge flow to control a much larger flow, for

example the feed to the reactor, can be ruled out

since valve saturation is likely during transients. In

the results given below, only RGA pairings between

0.5 and 4.0 are considered acceptable. Lastly, a

linear valve saturation analysis (Skogestad

and

Wolff, 1992) can be carried out based on the process

steady-state gains. Schemes in which valves saturate

are ruled out.

Of the 36 cases, only 4 passed all the screening

tests. In all 4 schemes reactor pressure is paired with

A-feed flow, reactor temperature with reactor cool-

ing temperature, stripper temperature with steam

flow and compressor power with the recycle valve

around the compressor. Table 5 shows the RGAs

for the four candidate control systems. The next step

in the analysis is to compare the steady-state ability

of these schemes to reject disturbances.

step 3

The ultimate goal of the final control system is to

keep both the product flow and composition as close

to the setpoints as possible in spite of upsets. In

Steps 1 and 2 above, product compositions and flows

are not considered explicitly. Downs

and Vogel

(1991) have presented an approach, based upon a

paper by Luyben (1975), through which the ability

of a plant’s basic PID control system to reject

disturbances on the more important product vari-

ables can be assessed. This approach is used here to

screen the 4 schemes which result from Step 2 and

then select candidate schemes for dynamic simula-

tion.

To carry out Downs and Vogel’s approach, one

considers each significant upset one at a time. Table

1 lists these upsets. As mentioned earlier, closing

the cascade loops effectively compensates for upsets

IDV(4),

IDV(S),

IDV(7),

IDV(ll),

IDV(12),

IDV(14)

and IDV(l5).

Further, it was found that

upset IDV(3) was very easy to control and it causes

no problems.

Thus,

at this step only IDV(l),

IDV(2)

and IDV(6)

need to be examined. Upset

IDV(6)

is discussed separately below. To analyze

for IDV(l),

a plot of the steady-state product flow

and composition,

shown in Fig. 5, is made as a

function of the size of the disturbance. To make this

plot one has to solve the nonlinear steady state

process model. What one desires in the basic PID

control system is a scheme that inherently has the

ability to reject disturbances without the use of the

analyzer. If such performance can be achieved then

the task of the analyzer control loops will be that

much easier. Figure 5 shows that in the face of the

IDV(l)

upset, all four schemes perform about the

same. A perfect control scheme would

keep all

product variables exactly at their setpoints. A simi-

lar plot can be made for IDV(2)

and it is shown in

Fig. 6. The fact that the plots for the four schemes

end at IDV(2) = 0.30 is indicative of the fact that if

the purge flow is held constant then the B material

balance cannot be met, and the steady-state equa-

tions have no solution. Figure 7 shows the same plot

as Fig. 6, but with the purge used to control the

composition of B in the purge stream. Now, the full

effect of upset IDV(2)

can be handled. It can be

concluded that to handle IDV(Z),

the purge should

be used to control the composition of B in the purge

stream. As Fig. 7 shows, there is little difference

between the four candidate schemes. In carrying out

this disturbance analysis, one can also assess poten-

tial valve saturation problems using the complete

nonlinear model,

as compared

to using linear

approaches (Skogestad and Wolff,

1992). For all

four schemes all valves are safely within their satur-

ation limits.

Next IDV(6)

is considered. IDV (6) involves the

loss of the A feed stream which is manipulated to

control pressure. This upset is similar to IDV(2)

in

that it results in an imbalance of gaseous compo-

nents entering and leaving the plant. The excess gas

can only be eliminated through the purge stream, or

by cutting back on the feed to the plant. In the case

of IDV(2)

additional B has to be removed.

For

normal plant operation the inputs of A and C are

roughly equal. When IDV(6)

occurs, the loss of A

means that excess C must be purged from the plant,

otherwise pressure will continue to rise. Purging the

excess C can be accomplished by switching the

pressure controller to the purge stream when the A

feed is lost. An examination of Fig. 4 shows that

after the A feed, the purge has the most important

effect on pressure. Using the purge to control pres-

sure gives rise to the RGAs

shown in Fig. 8, and

---

## Page 9

Base control for the Tennessee Eastman problem

391

these are acceptable.

Next,

a linear saturation

analy-

product flow, it would have to be manipulated

very

sis (Skogestad

and Wolff,

1992) is carried out and it

slowly. Thus,

it would not be effective

as a manipu-

shows that the purge valve will saturate when the A

lated variable.

Simply

leaving

product

flow out of

feed is lost. The purge stream simply cannot handle

the basic PID system resulted

in configurations

that

all of the excess

gas and

inerts

that

need

to be

were

inferior

in terms

of

their

ability

to

reject

eliminated.

One

possible

solution

is to lower the C

disturbances

to those when product

flow controlled

feed to the plant since it is this stream

that brings

stripper

level.

Similarly,

the use of reactor

coolant

in the excess gas as well as the inert B. However,

to

control

reactor

level

gave

very

poor

results.

in the 4 schemes

under

consideration,

the C feed

Not only did large RGAs

result,

but control

valve

is used

for

production

rate

control.

Thus,

this

saturation

problems

resulted

as well.

No

viable

approach

to IDV(6)

requires

that

production

be

pairings were found

when such a level scheme

was

cut back.

examined.

TO verify these conclusions,

Fig. 9 was developed

for steady-state

analysis of IDV(6).

For each of the

four

schemes,

the

purge

was

used

for

pressure

control.

When

the purge

valve reached

90%

of its

full open value,

then the production

rate was low-

ered.

In calculating

steady

state conditions,

it was

found useful to ratio the compressor

power,

reactor

feed (scheme

4), and compressor

exit flow (scheme

2) to the product

Row set point.

These

same ratios

are

used

in

the

dynamic

simulations

discussed

below.

Before

the product

flow set point is ratioed,

it is sent through

a 2 h time lag to avoid sudden step

changes

from

affecting

the ratioed

variables.

The

value

90%

for the purge

valve

is arbitrary,

but is

chosen

so that even after the A feed loss the purge

can still have some rangeability

for control.

Figure 9

shows that when IDV(6)

exceeds

0.7.

a steady-state

solution cannot be found for scheme 3. Similarly,

for

scheme

1 a steady-state

solution

cannot

be found

when IDV(6)

exceeds

0.87.

In both cases with the

purge fixed at 90%,

too much excess C remains

in

the system

for steady-state

to be achieved.

Thus,

schemes

1 and

3 are eliminated.

The

other

two

schemes

are very close in their steady state ability in

so far as IDV(6)

is concerned.

For both schemes

2

and 4, the condenser

cooling temperature

is lowered

in the face of IDV(6).

This lowering

of temperature

allows more liquid to flow out with the product,

and

therefore

less gas builds up. Clearly,

for scheme

1

one could consider

lowering the condenser

exit cool-

ing

water

temperature

setpoint

when

IDV(6)

occurs.

Alternatively,

for

scheme

3

one

could

consider

lowering

the

separator

temperature

set-

point

when

lDV(6)

occurs.

Neither

of these

two

alternatives

is considered

here.

step 4

The

last step in the analysis involves

tuning the

various

control

loops

and dynamic

simulation

to

assess

the

system’s

response

to

disturbances.

In

tuning loops,

the same order that is used in Steps l-

3 is used. First, the inner loops of the cascades

are

tuned.

Then

the level

loops

are tuned.

Next,

the

remaining,

noncomposition/production

rate

loops

are tuned.

Finally

the composition

and production

rate loops are tuned.

Initial loop tuning was carried

out with no noise in the simulation.

Then,

noise was

added and only flow loops and the two temperature

coolant

loops

were detuned.

For both the stripper

level-product

flow and reactor

pressure-A

feed

loops the controllers

are tuned to give an averaging

type control

response

(McDonald

et al.,

1986)

to

meet

the constraints

on how fast the two manipu-

lated variables

can move.

Also

an averaging

pres-

sure control

approach

is used for the purge flow-

pressure loop for the IDV(6)

upset. The production

rate-C

feed loop and the product

mix-D/E

ratio

loop

are also tuned

to respond

slowly enough

that

the constraints

on the rate of change in the various

flows are satisfied.

Finally,

the temperature

setpoint

for the stripper control is used to control the E mole

fraction in the product

in a double

cascade arrange-

ment. After tuning and simulation,

it was found that

the two remaining

schemes

gave almost

equivalent

performance.

In the results given below,

scheme 4 is

used.

In all cases PI controllers

are used and the

resulting controller

parameters

are given in Table 6.

The final plant control

scheme

is shown in Fig. 10.

The next step in the analysis involves

tuning the

various

control

loops

and

carrying

out

dynamic

simulation.

Before

discussing this step, the results of

carrying

out Steps

l-3

for the other

level control

configurations

will

be

summarized.

First,

when

steam flow is used to control

the stripper level, then

product

flow is available

for other

uses. However,

because

of the restrictions

on the rate of change of

One

last

point

can

be

noted.

When

IDV(6)

occurs,

the production

rate setpoint is stepped

down

by 23.8%,

as indicated

by the steady-state

analysis

shown

in Fig. 9. During

the transient

produced

by

IDV(6),

the purge valve saturated

for a period

of

time. However,

at steady-state

the valve came back

to 90%

open.

For the purge

flow pressure

loop

a

controller

gain

of

-0.00352

kscfm/kPa

was

used

with a reset time of 100 min.

CACE

18:5-C

---

## Page 10

T. J. McAvov

and N. YE

Disturbance Analysis

0.0

0.2

0.4

0.6

0.8

1.0

~W)

-- ___-___-

--_-

-_-_-_

0.0

0.2

O-4

0.6

0.8

1.0

IDW)

-m-e______

-___

-_-___

0.0

0.2

0.4

O-l5

0.8

1.0

rDV(1)

Fig. 5

---

## Page 11

Base control for the Tennessee Eastman problem

393

. -.

. . _ ’

-

0’.

.

-.

.

.

_.

-1

_

_

_.

-

-

-

_.

n

-

-.

‘.

-.

.

.

-(l)

.___--__._-_

-

(2)

----_

-01

__-___-

8ehune (4)

.

. .

.

.

. .

. .

I.

* .

.

. L...

I . . . . . . .

..I

.

.

.

.

.

.

.

.

.

0.00

0.10

IS&

0.30

0.40

54.5

. . . . . . . . _

1

-.

_.

-.

-.

1.

_.

.

-.

.

.

-‘to

__-_--___--_

----_

=p=&

2. h3

-_-_-__

scheme (4)

52.5

.

. .

.

. .

. .

. I..

.

.

. .

.

. . 1 .

.

.

* . .

. . .

. .

.

. .

.

.

.

. .

0.00

0.10

0.20

0.30

0.40

DV(2)

45 .O

scheme (1)

__---__-.-._

----_

izzEf I!

-_-_-_-

scheme (4)

44.5 -

43.0

..*......1.........,.........,.........-

0.00

0.10

020

0.30

0.40

IDV(2)

Fig. 6. Disturbance

analysis (purge B composition not controlled).

---

## Page 12

394

T. J. McAvov

and N. YE

..*___._-_

--__

m(3)

-m-.-e

@+==(4)

A"

4

21

0.0

0.2

0.4

0.6

0.8

1.0

~W2)

57

___..____*

56

-NM_

:j

---_--

1

55

u

54

53

52

0.0

0.4

0.6

0.8

1.0

=w2>

46

-*.____*_*

---_

-_-_-_

44

% 42

Fig. 7. Disturbance

analysis

<purge

B composition

not controlled).

---

## Page 13

Base control for the Tennessee

Eastman problem

SCHEME(

1)

395

rea.

temp.

fea.

presu.

strip

temp

camp

pow

purge flow

steam flow

setpoint

setpoint

-0.019

-0.017

w

0.027

0.020

@

-0.084

I

-0.009

T

1

rea. cooling

I

camp

recycle

setpoint

valve

I

@

0.018

-0.025

I

-0.085

I

SCHEME(2)

purge

flow

steam flow

rea. cooling

cond.

cooling

camp recycle

setpoint

setpoint

setpoint

setpoint

valve

rea. temp.

-0.006

-0.035

@

0.069

-0.008

rea. presu.

@

0.056

-0.043

-0.504

0.169

strip temp

0.004

@

-0.019

-0.054

-0.000

camp pow

-0.109

-0.029

0.039

0.389

@

feed react

-0.213

-0.061

0.043

0.131

Fig. 8

---

## Page 14

3%

T. J. McAvov

and N. YE

SCHEME(S)

purge flow

steam

flow

rea.

cooling

cond . cooling

camp

recycle

setpoint

setpoint

setpoint

setpoint

valve

rea.

temp.

-0.032

0.002

@

-0.072

0.046

rea.

presu.

@

0.001

-0.009

0.445

-0.308

strip temp

0.029

@

-0.024

0.031

0.006

camp

pow

-0.089

-0.013

0.032

0.085

@

sepa temp

0.222

0.052

-0.055

0.270

SCHEME(4)

purge flow

steam

flow

rea. cooling

cond.

cooling

camp

recycle

setpoint

setpoint

setpoint

setpoint

valve

rea.

temp.

-0.008

-0.032

@

0.057

-0.004

rea.

presu.

@

0.050

-0.039

-0.392

0.112

strip temp

0.013

@

-0.021

-0.023

0.002

camp

pow

-0.100

-0.022

0.036

0.257

@

recyc flow

-0.174

-0.024

0.037

0.060

Fig. S-Continued

---

## Page 15

Base control

for the Tennessee

Eastman

problem

397

G

20-

_.......-.

_---

18 -

_.-.-.

0.0

0.2

0.4

0.6

0.8

1.0

mV6)

53

.

I

I

I

q

0.0

0.2

0.4

0.6

0.8

1.0

IDv(9

46-

.

I

-

(1)

. . .._._.--

-

(2)

---_

schme3

_._.-.

schme4 i!

42 -

38

1

,

I

I

0.0

0.2

0.4

0.6

0.8

1.0

IDv(6)

Fig. 9.

Disturbance

analysis (compressor

power,

recycle and feed to reactor

ratio to product

sctpoint).

---

## Page 16

398

T. J. Mc-Avov

and N. Yt.

Tahlc ha

PI paramctcrs (cascade

inner loops)

Amfccd Row

D-feed

flow

E-feed

Row

Cmfccd flow

P

200 (‘%>/kacmh)

().I)02 (‘%./kg/h)

O.(W)2 (%/kg/h)

0.1 (%/kanh)

T, (min)

0. I

0.3

0.3

0.3

Scpar;itnr

under

Strip ~rndcr

Strip stcarn

Purge Row

Row

Row

Row

P

100 (‘Mkscmh)

0.3 (‘iilm’lh)

0.5 (‘%/m’/h)

0.03 (‘%/kg/h)

T, (min)

0.3

0.3

u.3

0.3

Reactor

cooling

Separator

cooling

tcmpcratllre

tcmpcraturc

P

- IO (‘Y /“C)

”

-10

(‘Y /“C)

”

T, (min)

I

I

Table hb

Rcnctor

Reactor

Strippcr

Compressor

tcmpcrat”rc

prcssurc

tcmperaturc

powc r

P

1.0

-O.(K)32 (kscmh/kPa)

10.0 (kg/hl”C)

0.0X (‘Y /kW)

”

T, (min)

SO

3(X)

IO

20

Reactor

Separator

Stripper

Purge B

lcvcl

lcvcl

ICVCI

composition

P

SOU (kg/h/%.)

-2.5

(m’lh/‘%)

-0.5

(m’/h/“L.)

-0.03

(kacmh/‘b)

7; (min)

2(H)

2(K)

3w

I (XI

Product

Product

Recycle

Product

E

flow

G/II

ratio

flow

composition

P

0.0X (kscmhlm’lh)

0.05

I .5 (“Clkscmh)

-0.5

(“CI%)

r, (min)

45

40

50

1UiJ

step

2

At Step 2 manipulated

and/or

controlled

variables

are eliminated

based upon operating

considerations

and examination

of the process

gain matrix.

For the

gain matrix given in Fig. 4, product

flow and E feed

are used to control

levels.

Following

the discussion

given under Stage 3 above,

D/E

should

be used for

control

of product

mix. Also,

since the product

flow

is used for level control,

the C feed must bc used for

production

rate control.

Thus,

these

two manipu-

lated

variables

can be eliminated.

An examination

of the gain matrix in Fig. 4 shows very strong corre-

lation

between

the agitator

speed

and the reactor

cooling

temperature

setpoint.

Column

9 is almost

a

constant

multiple

of column

6. Further

all of the

pressure

measurements

are

strongly

correlated.

Rows 3, 8 and 9 are almost constant

muhiples

of one

another.

Thus,

it will

be

extremely

difficult

to

manipulate

agitator

speed

and reactor

coding

inde-

pendently

and therefore

agitator

speed

is dropped.

It wit1 also

be

very

difficult

to control

all three

pressures

and therefore

only the reactor

pressure

is

retained.

Clearly,

a singular

value

decomposition

analysis (Smith et uf., 1981) could be used to get the

same

insights.

Dropping

agitator

speed

and

the

separator

and stripper

pressures

results

in a 7 x 6

problem.

Next,

a relative

gain

analysis

(Bristol,

1966)

is

carried out to determine

loop pairings.

The stability

of

the

resulting

loops

is

checked

using

the

Niederlinski

Index

(Niederlinski.

1971).

To

carry

out an RCA

analysis on the 7 x 6 problem,

one of

the controlled

variables

has to be eliminated.

If all 7

controlled

variables

were eliminated

one at a time,

then there

would

be 7 (6 x 6) RGAs

to consider.

However,

in any realistic

control

system,

some

of

the process

variables

must be under control.

In the

present

case these

variables

would

include

reactor

temperature

and pressure.

In addition,

since strip-

per temperature

reflects product

composition,

it will

also have to be controlled.

Finally,

it is decided

to

control

compressor

work.

Thus,

the controlled

vari-

ables

that

will

be eliminated

one

at a time

are:

reactor

feed

flow,

compressor

exit flow and separ-

ator

temperature.

Deciding

that

certain

variables

---

## Page 17

Base

control

for the Tennessee

Eastman

problem

399

---

## Page 18

400

T.J. Mc~Avov

and N. YE

24.0

55

a

d

23.5

6

E

II

54

0

f

w

23.0

i

53

22.5

1.0

.-..-...-I’-.------‘-----‘-‘-‘.....’..-

4am

0-a -

.

. . . . . . . ..I.-.......‘.....

-.-‘..-.-.-.*

0

10

20

30

40

Timc(kwrs)

34a

a-‘-.-‘-.-I--..‘--..

,.........,.........I.........

10

20

30

40

Time (bows)

5ooo

.-.....‘-I...-.‘...‘-.---“--‘.-----.-.

9.6'---.-.-.-1-........'.-."-'.--.......

a

ti 4600-

$""1

w

4Ooo . . ..-....I-.-.-.-.-'-----.---'---------

8_4,.--.-.;-1-...-..r..--.....'..--.....

0

10

20

30

40

0

10

20

30

40

Thne(homs)

Tiit(ham)

Fig. I la.

IDV(

I).

---

## Page 19

Base control

for the Tennessee

Eastman

problem

401

i O-Y

Loo-

%

0.04 -

0.02 -

0.00

0.1

1.0

10-O

100.0

0.1

1.0

10.0

Imo

I/Hour

0.1

1.0

10.0

imo

lltlor

a060

a050

a010

a000

aI

1.0

la0

lmo

l/n-=

Fig. I Ih. iDV(

I) (Fourier

coellicients).

---

## Page 20

402

T. J. Mc.Avov

and N. YE

0

10

20

30

40

a

10

20

30

40

Time (hours)

Time (hours)

0.8

4200

4wo

0.6

zi

3800

i

OA

LCO

4

P

0.2

3400

0.0

0

3200

10

20

30

40

0

10

20

30

40

Tie

(hours)

Tie

(hours)

4800

9.6

W

u

9.2

4200

t

1

c

’

4OlJO*

0

10

20

30

40

Time (hours)

9mL-..---..~--.---.-.~-.-..~~--~-.~---~-~I

0

10

20

30

40

Time (bars)

Fig. 12a. IDV(8).

---

## Page 21

Base cc>ntrol for the Tennessee

Eastman

problem

4.03

0.30

i!

6

0.m

f

0.10

_

o.oor

. . . . . ..I

0.1

1.0

IQ0

lmo

lniaur

0

0.1

1.0

10.0

1mo

l/H-

0.1

1.0

109

lrno

lrn-

no]

-

-

--“-I

.

.

.

--“-I

-

.

.

“‘“1

t

I

0.1

1.0

IO.0

lmo

1ilioUr

0.1

1.0

10.0

Imo

IMopr

Fig. 12h.

IDV(X)

(Fourier

cocflicicnts).

---

## Page 22

T. J. McAvov

and N. YE

26’.....“‘1-‘-‘-“..“-~......1..‘...-’-’

56

55

2A-

la,....-~....I.-.......I.........I--.-..-.u

0

‘.lO

20

30

40

-

0,’

10’

20

30

40

Tima (hours)

l-me <bars)

,

0.0...,....,.1...-..-.-‘.....“..’....-...-

0

10

20

30

40

Time (hours)

0

10

20

30

40

Tiie (hours)

Fig. ISa. Product

flowratc

sctpoint

changc:e-15%

---

## Page 23

Base control

for the Tennessee

Eastman

problem

405

50

Y)

i”

$m

IO

0

0.1

1.0

10.0

1woVr

al5 I

c

I

i

B

0.10

D

ii

am

0.00

0.1

1.0

loo.0

1N

0.1

1.0

ma

loao

1Ma

al

Fig. 1%.

Product

flowrutc

setpoint

change--15%

(Fourier

coefficients).

---

## Page 24

T. J. MC-Avou

and N. YE

=O~O 0

Tie

(hours)

Y

2

E

0.28

i

<

0.26

0.24;

0

10

20

30

40

Tiie (hours)

4wol

0

10

m

30

40

Time (hours)

_ Gcuqositia~

__..--.

Hcunpodtim

40 . . . . . . . ..‘...-..---‘..-.....-‘..I..-.-.

0

10

20

30

40

Time (hours)

r

8.88

0

10

m

30

40

Time (hours)

Fig. 14a. Product

G/H

ratio sctpoint

change from SO/SO to 40/M)

---

## Page 25

Base control

for the Tennessee

Eastman

problem

407

0.10

1

.-..--

O.OO-

P(Y-

O.DI-

I

I

c

i

O&Z-

0.1

1.0

10.0

lmmw

am2 F

o.oao

0.a

1.0

lo.0

1-0

lrn-

1.0

10.0

loa

I_

ai

1.0

lo.0

loo.0

lmow

1.0

ion

ai

1.0

lM

loao

I*

Fig. 14b. Product

G/H

ratio setpnint

change from StWW to 4.0/6tO (Fourier

coefficients)

UCE

18:5-O

---

## Page 26

408

T. J. M~Avou

and N. YE

24.0.

-..-

_‘-.-‘...

-=..-..

-.-‘..

-...-._

22.0‘.......

. . . .

. . . . ..-..-

...b..

1

0

IO

20

30

40

0

10

20

30

40

Time (hours)

Time (hours)

3800

3600

35oOd

0

10

20

30

40

Time (hours)

4600

_I

0

10

20

30

40

Time (hours)

2720[

’

-.-..“‘.-‘..-““-‘...“.~

2640

IL---------’

262otL..-..

-.

...........-...

. . . . . . . . . ...1

0

10

20

30

40

Time (hours)

---

## Page 27

Base control

for the Tennessee

Eastman

problem

409

0.a

? O.O

2

%

0.0

0.c

I

I

1 1

1

Q

Lo

0.1

1.0

IO.0

tmour

0.15

i

:I

i;g

0.10

0

%

0.05

_i;

1

0.1

1.0

10.0

100.0

0.1

1.0

10.0

100.0

1mour

rm0u

5

0

0.1

1.0

10.0

l/Hour

Fig. 15b.

Reactor

pressure

setpoint

change--60

kPa (Fourier

coefficients).

---

## Page 28

410

T. J. McAvov

and N. YE

22.4f.....-...,.......-....-..

. . ..-..-

0

10

20

30

40

Time (hours)

0

10

20

30

40

Time (bows)

2

3700

;

3600

u

P

0.22 -

0.20:

3500

0

10

20

30

40

0

10

20

30

40

Time (hours)

Tie

(halls)

4700

9.50

3

4600

9.40

s

!45,

I $

9.30

9.20

w

4400

V

9.10

Time (hours)

Tic

(hours)

0

10

20

30

40

Tie

(hours)

Fig. 16a. Purge

B composition

setpoint

change

2%.

---

## Page 29

Base control for the Tennessee Eastman problem

411

o.-

O.W?O

IO

1

o.oo2o

i

<

P

5

0.0010

O.WW

0

0.1

1.0

10.0

0.1

1.0

lrnW

mom

O.OW

0.1

1.0

10.0

lrn-

Fig. 16b. Purge B composition setpoint change 2% (Fourier coefficients).

---

## Page 30

412

T. J. McAvov

and N. YE

CONTROL

SYSTEM

RESULTS

In their paper,

Downs

and Vogel

suggested

that

the following

setpoint

changes

and upsets

be con-

sidered

in evaluating

potential

control

schemes:

IDV(

1)

Step change

IDV(4)

Step change

IDV(S)

Random

variation

IDV(12),

IDV(1.5)

Simultaneous

random

variation

and sticking

valve

Production

rate

Step change

- 15%

Product

mix

Step change

50/50-40160

G/H

Pressure

change

Step change

-60

kPa

Composition

of B

Step change

2%

For comparison

purposes

they also suggested

pre-

senting the frequency

content

of process

flowrates

to

these

upsets.

The

subroutine

FFTRF

in the IMSL

Math/Library

was used

to calculate

the frequency

spectra

of the flowrates.

FFTRF

computes

the dis-

crete Fourier

transform

of a real vector of size N. In

FFTRF,

it is assumed

that the real vector

repeats

itself periodically.

In our calculations,

N=

8000 and

the corresponding

time

is 40 h. The

Fourier

coef-

ficients

calculated

by FFTRF

are divided

by N/2.

Using

this approach

for

a unity

amplitude

cosine

function

of frequency

w, gives Fourier

coefficients

which are all zero except

at the frequency

w where

the Fourier

coefficient

equals

1.

Our

base

control

system

gave

almost

perfect

results for IDV(4)

and the IDV(

12) + IDV(

15) com-

bination.

Thus,

responses

to these

upsets

are not

shown.

Figures

11-16

give

the

results

for

the

remaining

disturbances,

together

with the frequency

content

of the process

flows.

As can be seen,

some

of the responses

can take as long as 20-40

h to die

out. This long transient

period

is due to the recycle

nature

of the plant.

In all cases tested,

all control

valves remained

within their saturation

limits. Thus,

the scheme

presented

provides

an acceptable

solu-

tion

to the

plant

wide

control

problem

that

was

posed.

Our

results

can be used as a basis to judge

the benefits

and improvements

that can be achieved

from more advanced

control

approaches.

In another

paper (Ye

and McAvoy,

1993)

we discuss the bene-

fits that

can

be

gotten

from

the

use

of

optimal

averaging

level control

(McDonald

et al.,

1986)

on

the Tennessee

Eastman

problem.

CONCLUSIONS

This

paper

has

presented

a methodology

for

designing

a base,

decentralized

PID control

system

for the Tennessee

Eastman

Control

Problem.

The

methodology

involves

screening

various

alternative

designs

using

steady-state

techniques

such

as the

RGA,

Niederlinski

Index,

and disturbance

analysis.

Engineering

judgement

is also

employed.

After,

reducing

the number

of alternatives,

dynamic

simu-

lation is used to tune Ioops and compare

alternatives

to arrive at a fin al scheme.

The

approach

used

produces

a final design

that

meets all of the requirements

posed

in the problem.

It is shown

that for one upset where

the A feed

is

lost, a selector

coupled

with a production

cutback

is

required

to

keep

pressure

under

control.

The

control

scheme

presented

can be used both to com-

pare the improvements

attained

with an advanced

control

approach

and as base system

upon which an

advanced

scheme

can be placed.

REFERENCES

Bristol E. On a new measure of interaction for multi-

variable process control. IEEE

Trans.

Autom.

Control

AC-11,

133 (1966).

Chylla R. and D. R. Haase, Temperature

control of a

semibatch

polymerization

reactor.

Compufers

them.

Enana

17. 257-264

(1993).

Cutler C. and B. Ramaker,

Dynamic matrix control: a

computer

controt

algorithm.

RIChE

86fh

National

Mee&g,

Paper 51b, Houston. TX (1975)).

Downs J. and E. Vogel,

A plant-wide industrial process

control problem.

Computers

chcm.

Engng

17, 245-255

(1993).

Forbes J., I‘. Marlin and J. Macgregor,

Model accuracy

requirements for ecomonic optimizing model predictive

controllers-the

linear

programming

case.

PrOC.

American

Control

Conf.,

Chicago,

IL, pp. lS87-1593

(1992).

Luyben W.

Steady state energy conversation aspects of

distillation column

control

system

design.

I &

EC

Fundum.

14, 321-325

(1975).

McAvoy

T. Inreracrion Analysis.

ISA, Research Triangle

Park, NC, pp. 34-37

(1983).

McDonald

K.. T. McAvov and A. Tits. Ootimal averaeine

level control. AiChE

Ji 32, 75-86

(i98;).

-

-

McFarIane R., R. Reineman, J. Bartee and C. Georgakis,

A dynamic simulator for a model

IV fluid catalytic

cracking unit.

Computers

them.

Engng

17,

275-300

(1993).

Niederlinski A.

A heuristic approach to the design of

linear multivariable control systems. Automatica

7, 691

(1971).

Piovoso M., K. Kosanovich and R. Pearson, Monitoring

process

performance

in real-time.

Pruc.

American

Control

Conf.,

pp. 2359-2363

(1992).

Prett D. and M. Morari, Shell Process

Control

Workshop.

Butterworths, Stoneham, MA (1986).

Skogestad S. and E. Wolff,

Controllability

measures for

disturbance

rejection.

Proc.

of

IFAC

Workshop

on

Interactions

Between

Process

Design

and

Process

Control,

London, pp. 23-30

(1992).

Smith C.. C. Moore and D. Bruns. A structural framework

for

mLtlivariable

control

an&cations.

Proc.

JACC

Meedng,

Session TA-7,

Charlottsville, VA (1981).

Ricker NY, J. Lee and Y. Chikkula, Optimal operation and

control of the Tennessee Eastman Challenge process.

Submitted

for presentation

at 1993

Annual

AIChE

Meering,

St Louis, MO (1993).

---

## Page 31

Base control for the Tennessee Eastman problem

413

Vogel

E. and J. Downs,

Process modeling for control

Ye N. and T. McAvoy.

Optimal averaging level control

strategy development.

Presented at 6rh Biennial Short

applied to the Tennessee Eastman Plant. Submitted for

Course

on Applications

of Advanced

Control

in the

presentation at 1993 Annual AZChE Meeting, St Louis,

Chemical Process Industries. College Park, MD (1991).

MO (1993).

---

