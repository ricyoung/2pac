# 2PAC Workflow 

## Complete Processing Workflow

```
┌─────────────────┐
│ Start Scan      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Find Image Files│────▶│ Resume from      │
└────────┬────────┘     │ Previous Session │
         │              └──────────────────┘
         ▼
┌─────────────────┐
│ Process Files   │
│ in Parallel     │
└────────┬────────┘
         │
         ▼
     ┌───┴───┐
     │       │
     ▼       ▼
┌─────────┐ ┌─────────┐
│ Valid   │ │ Invalid │
│ Images  │ │ Images  │
└─────────┘ └────┬────┘
                 │
                 ▼
            ┌────┴─────┐
            │ Repair?  │
            └──┬───────┘
            ┌──┴───┐
            │      │
  ┌─────────▼──┐ ┌─▼──────────┐
  │ Attempt    │ │ Handle     │
  │ Repair     │ │ Unrepaired │
  └──┬──────┬──┘ └─┬──────────┘
     │      │      │
     │      │      ▼
     │ ┌────▼──────┴─────┐
     │ │ Report Results  │
     │ └──────────┬──────┘
     │            │
     │            ▼
     │     ┌──────┴─────┐
     │     │ Save       │
     │     │ Progress   │
     │     └──────┬─────┘
     │            │
     │            ▼
     │     ┌──────┴─────┐
     │     │ End Scan   │
     │     └────────────┘
     │
     ▼
┌─────────────┐
│ Repair      │
│ Successful? │
└─────┬───┬───┘
      │   │
      │   └───────┐
      ▼           ▼
┌──────────┐ ┌────────┐
│ Keep     │ │ Report │
│ Repaired │ │ Failed │
│ Image    │ │ Repair │
└──────────┘ └────────┘
```

## Detailed Validation Process

```
┌─────────────────┐
│ Image File      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐           ┌─────────────────┐
│ Basic Validation │──────────▶│ Validation      │
│ (Headers & Data) │           │ Sensitivity     │
└────────┬────────┘           │ (low/med/high)  │
         │                    └────────┬────────┘
         │                             │
         │                             ▼
         │                    ┌─────────────────┐
         │                    │ Format-Specific  │
         │                    │ Validation      │
         │                    └────────┬────────┘
         │                             │
         ▼                             ▼
┌─────────────────┐           ┌─────────────────┐
│ Visual Content  │◀──────────│ Technical       │
│ Analysis        │           │ Validation      │
└────────┬────────┘           │ Results         │
         │                    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Apply Visual    │
│ Strictness      │
│ (low/med/high)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Final Validation│
│ Decision        │
└────────┬────────┘
         │
         ▼
     ┌───┴───┐
     │       │
     ▼       ▼
┌─────────┐ ┌─────────┐
│ Valid   │ │ Invalid │
│ Images  │ │ Images  │
└─────────┘ └─────────┘
```

## Visual Corruption Detection Process

```
┌─────────────────┐
│ Image Content   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Sample Image    │
│ Pixels          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analyze Color   │
│ Distribution    │
└────────┬────────┘
         │
      ┌──┴──┐
      │     │
      ▼     ▼
┌─────────┐ ┌─────────────┐
│ Check   │ │ Check Large │
│ Color   │ │ Uniform     │
│ Pattern │ │ Areas       │
└────┬────┘ └──────┬──────┘
     │             │
     ▼             ▼
┌────────────┐ ┌───────────────┐
│ Detect     │ │ Apply Context │
│ Unnatural  │ │ (Distinguish  │
│ Patterns   │ │ from natural  │
└──────┬─────┘ │ backgrounds)  │
       │       └───────┬───────┘
       │               │
       ▼               ▼
┌─────────────────────┴────────┐
│ Apply Strictness Threshold   │
│ (low/medium/high)            │
└────────────────┬─────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Final Decision:                 │
│ Visually Corrupt or Valid?      │
└─────────────────────────────────┘
```

## Repair Workflow

```
┌─────────────────┐
│ Corrupt Image   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Diagnose Issue  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create Backup   │
│ (if enabled)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Select Repair   │
│ Strategy        │
└────────┬────────┘
         │
         ▼
     ┌───┴────────────┐
     │                │
     ▼                ▼
┌─────────────┐  ┌──────────────┐
│ Fix Header  │  │ Re-encode    │
│ Issues      │  │ Image Data   │
└──────┬──────┘  └───────┬──────┘
       │                 │
       └────────┬────────┘
                │
                ▼
┌─────────────────────────┐
│ Validate Repaired Image │
└────────────┬────────────┘
             │
             ▼
         ┌───┴───┐
         │       │
         ▼       ▼
┌──────────────┐ ┌─────────────┐
│ Repair       │ │ Repair      │
│ Successful   │ │ Failed      │
└──────────────┘ └─────────────┘
```

## Progress Saving and Resumption System

```
┌─────────────────┐
│ Start Scan      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌───────────────┐
│ Create Session  │──────▶ Resume?       │
│ ID              │      └───────┬───────┘
└────────┬────────┘              │
         │                       │
         │              ┌────────┴───────┐
         │              │ Load Previous  │
         │              │ Session State  │
         │              └────────┬───────┘
         │                       │
         ▼                       ▼
┌─────────────────┐      ┌───────────────┐
│ Process Files   │◀─────│ Skip Already  │
│                 │      │ Processed     │
└────────┬────────┘      └───────────────┘
         │
         ▼
┌─────────────────┐      ┌───────────────┐
│ Save Progress   │◀─────│ Timer Interval│
│ Periodically    │      │ (Default: 5m) │
└────────┬────────┘      └───────────────┘
         │
┌────────┴────────┐
│ Handle Keyboard │
│ Interrupts      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Save Final      │
│ Progress State  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ End Session     │
└─────────────────┘
```

These flowcharts illustrate the comprehensive workflow of 2PAC, including the new visual corruption detection feature.