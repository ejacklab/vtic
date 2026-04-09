# TypeScript Top 5 Interview Questions (2025–2026)

**Source:** DataCamp, GeeksforGeeks, InterviewBit, Arc.dev, Turing

**Date:** 2026-03-15
**Time Spent:** ~37 seconds
**Start:** 23:43:15
**End:** 23:43:52

---

## 1. Interfaces vs Types

**When to choose:**

| Interface | Type |
|-----------|------|
| Object shapes | Union/Intersection types |
| Declaration merging needed | Primitives, tuples |
| Class implementation | Mapped types |
| Extending other interfaces | Conditional types |

**Example - Interface (declaration merging):**
```typescript
interface User {
  name: string;
}

// Declaration merging - only works with interface!
interface User {
  email: string;
}

const user: User = {
  name: "Alice",
  email: "alice@example.com"  // Both merged!
};
```

**Example - Type (union/intersection):**
```typescript
type Status = "pending" | "approved" | "rejected";  // Union
type ID = string | number;  // Union

type User = { name: string } & { email: string };  // Intersection

// This CAN'T be done with interface:
type Point = [number, number];  // Tuple - interface can't do this
```

---

## 2. Generics

**Basic identity:**
```typescript
function identity<T>(arg: T): T {
  return arg;
}

const num = identity<number>(42);      // T = number
const str = identity("hello");          // T inferred as string
```

**Extended getProperty:**
```typescript
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

const user = { name: "Alice", age: 30 };
const name = getProperty(user, "name");   // string
const age = getProperty(user, "age");     // number
// getProperty(user, "email");            // Error! Not a key
```

**Why generics are needed:**
- Type safety without `any`
- Reusable code that works with multiple types
- Preserve type information (input T → output T)
- Compile-time type checking

---

## 3. any vs unknown vs never

```typescript
// any - OPT OUT of type checking (dangerous!)
let anything: any = "hello";
anything = 42;
anything.nonExistentMethod();  // No error at compile time (runtime crash!)
anything.foo.bar.baz;          // All allowed - use sparingly!

// unknown - type-safe counterpart of any
let uncertain: unknown = "hello";
uncertain = 42;

// uncertain.toUpperCase();    // Error! Can't use without narrowing
if (typeof uncertain === "string") {
  uncertain.toUpperCase();     // OK! Narrowed to string
}

// never - type that never occurs
function throwError(message: string): never {
  throw new Error(message);    // Never returns
}

function infiniteLoop(): never {
  while (true) {}              // Never returns
}

// Union narrowing to never
type Shape = "circle" | "square";
function getArea(shape: Shape): number {
  switch (shape) {
    case "circle": return Math.PI;
    case "square": return 1;
    default:
      const _exhaustive: never = shape;  // Compile error if new case added!
      return _exhaustive;
  }
}
```

**When to use:**

| Type | Use Case |
|------|----------|
| `any` | Migration from JS, prototyping (avoid in production) |
| `unknown` | External APIs, user input, safe alternative to any |
| `never` | Unreachable code, exhaustive checks, functions that throw |

---

## 4. Type Guards & Type Narrowing

```typescript
type Mixed = string | number | boolean;

// typeof guard
function process(value: Mixed): string {
  if (typeof value === "string") {
    return value.toUpperCase();      // Narrowed to string
  } else if (typeof value === "number") {
    return value.toFixed(2);         // Narrowed to number
  } else {
    return value ? "true" : "false"; // Narrowed to boolean
  }
}

// Custom type guard (is)
interface Fish { swim: () => void }
interface Bird { fly: () => void }
type Pet = Fish | Bird;

function isFish(pet: Pet): pet is Fish {
  return "swim" in pet;
}

function move(pet: Pet) {
  if (isFish(pet)) {
    pet.swim();   // TypeScript knows pet is Fish
  } else {
    pet.fly();    // TypeScript knows pet is Bird
  }
}

// in operator
type Config = { timeout: number } | { retries: number };

function getSetting(config: Config) {
  if ("timeout" in config) {
    console.log(config.timeout);  // Narrowed
  } else {
    console.log(config.retries);  // Narrowed
  }
}

// instanceof guard
class Dog { bark() {} }
class Cat { meow() {} }

function speak(animal: Dog | Cat) {
  if (animal instanceof Dog) {
    animal.bark();
  } else {
    animal.meow();
  }
}
```

---

## 5. Conditional Types & Utility Types

**Built-in utilities:**
```typescript
interface User {
  id: number;
  name: string;
  email: string;
  age: number;
}

// Extract - keep types that match
type StringOrNumber = string | number | boolean;
type Strings = Extract<StringOrNumber, string>;  // string

// Exclude - remove types that match
type NonString = Exclude<StringOrNumber, string>;  // number | boolean

// Pick - select specific properties
type UserPreview = Pick<User, "id" | "name">;
// { id: number; name: string }

// Omit - remove specific properties
type UserWithoutId = Omit<User, "id" | "age">;
// { name: string; email: string }

// Partial - make all optional
type PartialUser = Partial<User>;
// { id?: number; name?: string; email?: string; age?: number }
```

**Custom conditional type - IsString:**
```typescript
type IsString<T> = T extends string ? true : false;

type A = IsString<string>;   // true
type B = IsString<number>;   // false
type C = IsString<"hello">;  // true (literal)
type D = IsString<string | number>;  // true | false = boolean

// More advanced: check if string literal (not just string)
type IsStringLiteral<T> = T extends string 
  ? (string extends T ? false : true) 
  : false;

type E = IsStringLiteral<string>;   // false (not literal)
type F = IsStringLiteral<"hello">;  // true (literal)
type G = IsStringLiteral<number>;   // false

// Usage example
function echo<T extends string>(value: T): IsStringLiteral<T> extends true ? `Got: ${T}` : string {
  return (typeof value === 'string' ? `Got: ${value}` : value) as any;
}
```

---

## Summary

| # | Topic | Difficulty | Asked In |
|---|-------|------------|----------|
| 1 | Interfaces vs Types | ⭐⭐ | 90%+ of TS interviews |
| 2 | Generics | ⭐⭐⭐ | All senior roles |
| 3 | any vs unknown vs never | ⭐⭐ | Safety & narrowing questions |
| 4 | Type Guards | ⭐⭐⭐ | Type system mastery |
| 5 | Conditional & Utility Types | ⭐⭐⭐⭐ | Advanced positions |

---

*Generated by cclow (zai/glm-5)*
