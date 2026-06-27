// The full Glang learning path. Each module groups lesson modules imported from
// ./lessons/*.ts. Lessons appear in the sidebar and main view in this order.
import type { Lesson, LessonWithModule, Module } from '../types.ts'

import overview from './lessons/overview.ts'
import helloWorld from './lessons/hello-world.ts'
import running from './lessons/running-programs.ts'

import comments from './lessons/comments.ts'
import identifiers from './lessons/identifiers-keywords.ts'
import literals from './lessons/literals-escapes.ts'

import primitives from './lessons/primitives.ts'
import byteType from './lessons/the-byte-type.ts'
import casting from './lessons/casting.ts'
import pointers from './lessons/pointers.ts'
import arrays from './lessons/arrays.ts'
import nullable from './lessons/nullable.ts'
import enums from './lessons/enums.ts'

import declarations from './lessons/declarations.ts'
import constants from './lessons/constants.ts'

import arithmetic from './lessons/arithmetic.ts'
import comparisonLogical from './lessons/comparison-logical.ts'
import bitwise from './lessons/bitwise.ts'
import assignment from './lessons/assignment.ts'
import precedence from './lessons/precedence.ts'

import ifElse from './lessons/if-else.ts'
import whileLoops from './lessons/while-loops.ts'
import forLoops from './lessons/for-loops.ts'
import breakContinue from './lessons/break-continue.ts'
import returnStmt from './lessons/return.ts'

import definingFunctions from './lessons/defining-functions.ts'
import outParameters from './lessons/out-parameters.ts'
import recursion from './lessons/recursion.ts'
import builtinsIo from './lessons/builtins-io.ts'
import functionPointers from './lessons/function-pointers.ts'

import stackHeap from './lessons/stack-and-heap.ts'
import allocBlocks from './lessons/alloc-blocks.ts'
import objectsNewDelete from './lessons/objects-new-delete.ts'
import usingBlocks from './lessons/using-blocks.ts'

import definingClasses from './lessons/defining-classes.ts'
import inheritance from './lessons/inheritance.ts'
import staticMembers from './lessons/static-members.ts'
import operatorOverloading from './lessons/operator-overloading.ts'

import interfaces from './lessons/interfaces.ts'

import objectModifiers from './lessons/object-modifiers.ts'
import linq from './lessons/linq.ts'

import exceptions from './lessons/exceptions.ts'

import generics from './lessons/generics.ts'
import collections from './lessons/collections.ts'

import imports from './lessons/imports.ts'
import namespaces from './lessons/namespaces.ts'
import usingDeclarations from './lessons/using-declarations.ts'

import stdlibTour from './lessons/stdlib-tour.ts'

import memorySafety from './lessons/memory-safety.ts'
import spanMemoryOwner from './lessons/span-memoryowner.ts'

export const MODULES: Module[] = [
  { id: 'getting-started', title: 'Getting Started', icon: '◆', lessons: [overview, helloWorld, running] },
  { id: 'lexical', title: 'Lexical Structure', icon: '✎', lessons: [comments, identifiers, literals] },
  { id: 'types', title: 'Types', icon: '⬡', lessons: [primitives, byteType, casting, pointers, arrays, nullable, enums] },
  { id: 'variables', title: 'Variables', icon: '≡', lessons: [declarations, constants] },
  { id: 'operators', title: 'Operators', icon: '±', lessons: [arithmetic, comparisonLogical, bitwise, assignment, precedence] },
  { id: 'control-flow', title: 'Control Flow', icon: '⤳', lessons: [ifElse, whileLoops, forLoops, breakContinue, returnStmt] },
  { id: 'functions', title: 'Functions', icon: 'ƒ', lessons: [definingFunctions, outParameters, recursion, builtinsIo, functionPointers] },
  { id: 'memory', title: 'Memory Model', icon: '▤', lessons: [stackHeap, allocBlocks, objectsNewDelete, usingBlocks] },
  { id: 'classes', title: 'Classes', icon: '◍', lessons: [definingClasses, inheritance, staticMembers, operatorOverloading] },
  { id: 'interfaces', title: 'Interfaces', icon: '◇', lessons: [interfaces] },
  { id: 'modifiers', title: 'Object Modifiers', icon: '✛', lessons: [objectModifiers, linq] },
  { id: 'exceptions', title: 'Exceptions', icon: '!', lessons: [exceptions] },
  { id: 'generics', title: 'Generics', icon: '<>', lessons: [generics, collections] },
  { id: 'modules', title: 'Modules & Namespaces', icon: '⧉', lessons: [imports, namespaces, usingDeclarations] },
  { id: 'stdlib', title: 'Standard Library', icon: '⚒', lessons: [stdlibTour] },
  { id: 'safety', title: 'Memory Safety', icon: '⛨', lessons: [memorySafety, spanMemoryOwner] },
]

// Flattened lesson list with module back-references, for routing + prev/next.
export const ALL_LESSONS: LessonWithModule[] = MODULES.flatMap((m) =>
  m.lessons.map((l: Lesson) => ({ ...l, moduleId: m.id, moduleTitle: m.title })),
)

export const TOTAL_LESSONS = ALL_LESSONS.length

export function findLesson(id: string): {
  lesson: LessonWithModule | null
  prev: LessonWithModule | null
  next: LessonWithModule | null
  index: number
} {
  const idx = ALL_LESSONS.findIndex((l) => l.id === id)
  if (idx === -1) return { lesson: null, prev: null, next: null, index: -1 }
  return {
    lesson: ALL_LESSONS[idx],
    prev: idx > 0 ? ALL_LESSONS[idx - 1] : null,
    next: idx < ALL_LESSONS.length - 1 ? ALL_LESSONS[idx + 1] : null,
    index: idx,
  }
}
