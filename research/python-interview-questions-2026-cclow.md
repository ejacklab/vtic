# Python Top 5 Interview Questions (2026)

**Source:** LeetCode, Interviewing.io, Real Python, common interview patterns

**Answered by:** cclow (zai/glm-5)
**Date:** 2026-03-16
**Time Spent:** ~43 seconds
**Start:** 00:04:15
**End:** 00:04:58

---

## 1. Two Sum

**Problem:** Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to target. (You may assume exactly one solution.)

```python
def two_sum(nums: list[int], target: int) -> list[int]:
    """
    Time: O(n), Space: O(n)
    Use hash map to store complement -> index
    """
    seen = {}  # value -> index
    
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    
    return []  # No solution (shouldn't happen per problem)

# Example
nums = [2, 7, 11, 15]
target = 9
print(two_sum(nums, target))  # [0, 1]
```

**Why this works:** Single pass, check if complement exists before adding current number to avoid using same element twice.

**Alternative approaches:**
| Approach | Time | Space | Notes |
|----------|------|-------|-------|
| Brute force | O(n²) | O(1) | Check all pairs |
| Hash map | O(n) | O(n) | Best for unsorted |
| Two pointers | O(n log n) | O(1) | Requires sorting |

---

## 2. Valid Parentheses

**Problem:** Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, `'['` and `']'`, determine if the input string is valid (all brackets are properly closed and nested).

```python
def is_valid(s: str) -> bool:
    """
    Time: O(n), Space: O(n)
    Stack-based approach
    """
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:  # Closing bracket
            if not stack or stack.pop() != mapping[char]:
                return False
        else:  # Opening bracket
            stack.append(char)
    
    return len(stack) == 0  # Stack must be empty

# Examples
print(is_valid("()[]{}"))   # True
print(is_valid("([)]"))     # False (wrong nesting)
print(is_valid("{[]}"))     # True (correct nesting)
```

**Key insight:** Every closing bracket must match the most recent unmatched opening bracket (LIFO → stack).

**Edge cases:**
- Empty string → `True`
- Single bracket → `False`
- Unmatched opening → `False` (stack not empty)
- Unmatched closing → `False` (stack empty or wrong top)

---

## 3. Longest Substring Without Repeating Characters

**Problem:** Given a string `s`, find the length of the longest substring without repeating characters.

```python
def length_of_longest_substring(s: str) -> int:
    """
    Time: O(n), Space: O(min(n, alphabet))
    Sliding window with hash map
    """
    char_index = {}  # character -> last index
    left = 0
    max_length = 0
    
    for right, char in enumerate(s):
        if char in char_index and char_index[char] >= left:
            # Duplicate found, move left pointer
            left = char_index[char] + 1
        
        char_index[char] = right
        max_length = max(max_length, right - left + 1)
    
    return max_length

# Examples
print(length_of_longest_substring("abcabcbb"))  # 3 ("abc")
print(length_of_longest_substring("bbbbb"))     # 1 ("b")
print(length_of_longest_substring("pwwkew"))    # 3 ("wke")
```

**Sliding window logic:**
- `left` marks start of current substring
- When duplicate found, jump `left` past previous occurrence
- Track max length at each step

**Why use `char_index[char] >= left`:**
- Character might exist in map but be before current window
- Only move `left` if duplicate is within current window

---

## 4. Decorators with Real-World Example

**Problem:** Write a simple decorator that logs the execution time of any function. How does it work internally?

```python
import time
from functools import wraps

def timing_decorator(func):
    """
    Logs execution time of any function.
    """
    @wraps(func)  # Preserves function metadata
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    
    return wrapper

# Usage
@timing_decorator
def slow_function(n: int) -> int:
    """Sum numbers from 1 to n."""
    total = 0
    for i in range(1, n + 1):
        total += i
    return total

result = slow_function(1000000)
# Output: slow_function took 0.0523 seconds
print(f"Result: {result}")
```

**How it works internally:**
```python
# @timing_decorator is syntactic sugar for:
slow_function = timing_decorator(slow_function)

# When called:
# 1. wrapper() is invoked with args/kwargs
# 2. wrapper() calls original func()
# 3. wrapper() logs timing
# 4. wrapper() returns result
```

**Why `@wraps(func)`:**
- Preserves `__name__`, `__doc__`, `__module__`
- Without it, all decorated functions would show as `wrapper`

**Real-world decorator use cases:**

| Use Case | Example |
|----------|---------|
| Logging | Track function calls |
| Authentication | Check permissions before function |
| Caching | Memoize expensive results |
| Rate limiting | Throttle API calls |
| Retry logic | Auto-retry on failure |
| Validation | Validate inputs/outputs |

---

## 5. is vs == + *args / **kwargs

### is vs ==

```python
# == compares VALUES (equality)
# is compares IDENTITY (same object in memory)

a = [1, 2, 3]
b = [1, 2, 3]
c = a

print(a == b)  # True (same values)
print(a is b)  # False (different objects)
print(a is c)  # True (same object)

# When is returns True but == returns False:
x = float('nan')
y = float('nan')

print(x == y)   # False! (NaN != NaN by IEEE 754 spec)
print(x is y)   # False (different objects)

# Better example with singletons:
a = None
b = None
print(a is b)   # True (None is singleton)
print(a == b)   # True

# String interning:
s1 = "hello"
s2 = "hello"
print(s1 is s2)  # True (interned literal)

s3 = "hello" * 100
s4 = "hello" * 100
print(s3 is s4)  # False (not interned, too long)
print(s3 == s4)  # True (same value)
```

**Quick reference:**

| Operator | Compares | Use Case |
|----------|----------|----------|
| `==` | Value equality | Most comparisons |
| `is` | Object identity | `None`, singletons, type checks |

**When to use `is`:**
```python
# Checking None (recommended)
if x is None:  # ✅ Correct
if x == None:  # ❌ Not recommended

# Type checking
if type(x) is int:  # Exact type match
if isinstance(x, int):  # Includes subclasses (usually better)

# Sentinel values
_sentinel = object()
def foo(x=_sentinel):
    if x is _sentinel:
        # No argument provided
```

### *args and **kwargs

```python
def flexible_function(*args, **kwargs):
    """
    *args: Variable positional arguments (tuple)
    **kwargs: Variable keyword arguments (dict)
    """
    print(f"args: {args}, type: {type(args)}")
    print(f"kwargs: {kwargs}, type: {type(kwargs)}")
    
    total = sum(args) if args else 0
    
    for key, value in kwargs.items():
        print(f"  {key} = {value}")
    
    return total

# Usage
result = flexible_function(1, 2, 3, name="Alice", age=30, city="NYC")
# args: (1, 2, 3), type: <class 'tuple'>
# kwargs: {'name': 'Alice', 'age': 30, 'city': 'NYC'}, type: <class 'dict'>
#   name = Alice
#   age = 30
#   city = NYC
```

**Real-world example: wrapper function**
```python
def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

@log_call
def greet(name: str, greeting: str = "Hello"):
    return f"{greeting}, {name}!"

print(greet("Alice", greeting="Hi"))
# Calling greet with args=('Alice',), kwargs={'greeting': 'Hi'}
# Hi, Alice!
```

**Unpacking with * and **:**
```python
numbers = [1, 2, 3]
print(*numbers)  # 1 2 3 (unpacks list)

config = {'a': 1, 'b': 2}
foo(**config)  # Equivalent to foo(a=1, b=2)

# Merge dicts (Python 3.9+)
dict1 = {'a': 1}
dict2 = {'b': 2}
merged = {**dict1, **dict2}  # {'a': 1, 'b': 2}
```

**Quick reference:**

| Syntax | Meaning | Type | Example |
|--------|---------|------|---------|
| `*args` | Extra positional args | `tuple` | `func(1, 2, 3)` |
| `**kwargs` | Extra keyword args | `dict` | `func(a=1, b=2)` |
| `*` (unpack) | Expand iterable | - | `print(*[1,2,3])` |
| `**` (unpack) | Expand dict | - | `func(**{'a': 1})` |

---

## Summary

| # | Topic | Difficulty | Pattern |
|---|-------|------------|---------|
| 1 | Two Sum | ⭐⭐ | Hash Map |
| 2 | Valid Parentheses | ⭐⭐ | Stack |
| 3 | Longest Substring | ⭐⭐⭐ | Sliding Window |
| 4 | Decorators | ⭐⭐⭐ | Functions as objects |
| 5 | is/== + args/kwargs | ⭐⭐ | Core concepts |

---

*Generated by cclow (zai/glm-5)*
