# Async Risk Framework Architecture

This document explains the design and architecture of the event-driven asynchronous risk calculation framework built in Python. It supports plug-and-play risk models, incremental recalculation based on updated market data, and clear separation between pricing logic and risk model orchestration.

---

## Class Architecture

```mermaid
classDiagram
    class Instrument {
        - id: str
        - type: str
        + depends_on(): List[str]
        + Price(): float
    }

    class RiskModel {
        <<abstract>>
        + required_market_data(): List[str]
        + compute(instruments, market_data): Coroutine
    }

    RiskModel <|-- DiscountCurveModel : implements
    RiskModel <|-- ForwardCurveModel : implements
    

    class MultiModel {
        - models: List[RiskModel]
        + compute(instruments, market_data, changed_keys): Coroutine
    }

    class Env {
        + __enter__()
        + __exit__()
        + get(key): Any
    }

    Instrument --> Env : uses during Price()
    RiskModel --> Env : configures context
    MultiModel --> RiskModel : delegates compute()
```

---

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant Market as Market Data Feed
    participant MM as MultiModel
    participant RM1 as DiscountCurveModel
    participant RM2 as ForwardCurveModel
    participant Inst as Instrument
    participant Env as Env Context

    Market->>MM: New Tick (MarketData + ChangedKeys)
    MM->>RM1: compute([insts], market_data)
    RM1->>Env: with Env(DiscountCurve=X)
    Env-->>Inst: Env values
    RM1->>Inst: Price()
    Inst-->>RM1: Price Result
    RM1-->>MM: Partial Results

    MM->>RM2: compute([insts], market_data)
    RM2->>Env: with Env(ForwardCurve=Y)
    RM2->>Inst: Price()
    Inst-->>RM2: Price Result
    RM2-->>MM: Partial Results
    MM-->>Market: Final Risk Output
```

---

## Key Concepts

### 1. `Instrument`

* Knows its dependencies (e.g., DiscountCurve, ForwardCurve).
* Owns pricing logic inside `Price()` method.

### 2. `RiskModel`

* Declares which market data it needs.
* `compute()` method sets the appropriate data in `Env`, then calls `Instrument.Price()`.

### 3. `MultiModel`

* Delegates work to submodels based on intersection of:

  * Instrument's dependencies
  * Model's required market data
  * Actually changed market data

### 4. `Env`

* Singleton-like context manager using `contextvars`.
* Supports nested scopes and automatic restoration.

---

## Extension Ideas

* Integrate caching of previous instrument results.
* Model hierarchy (parent/child models) for composite risk views.
