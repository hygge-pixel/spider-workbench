// Spider Workbench: parse literal decoder data without executing input JavaScript.
import {parseExpression} from '@babel/parser';
import * as t from '@babel/types';

function literal(node: t.Node, depth = 0): unknown {
  if (depth > 100) throw new Error('literal nesting limit');
  if (t.isStringLiteral(node) || t.isNumericLiteral(node) || t.isBooleanLiteral(node)) return node.value;
  if (t.isNullLiteral(node)) return null;
  if (t.isArrayExpression(node)) return node.elements.map(item => {
    if (!item || t.isSpreadElement(item)) throw new Error('literal array required');
    return literal(item, depth + 1);
  });
  if (t.isObjectExpression(node) && node.properties.length === 0) return Object.create(null);
  if (t.isUnaryExpression(node) && ['+', '-', '!'].includes(node.operator)) {
    const value = literal(node.argument, depth + 1);
    if (node.operator === '!') return !value;
    if (typeof value !== 'number') throw new Error('numeric operand required');
    return node.operator === '-' ? -value : value;
  }
  // Packer commonly stores its dictionary as a literal string split on '|'.
  if (t.isCallExpression(node) && t.isMemberExpression(node.callee) && !node.callee.computed
      && t.isStringLiteral(node.callee.object) && t.isIdentifier(node.callee.property, {name:'split'})
      && node.arguments.length === 1 && t.isStringLiteral(node.arguments[0])) {
    return node.callee.object.value.split(node.arguments[0].value);
  }
  throw new Error('dynamic expression is not literal data');
}

export function staticValue(code: string): unknown {
  if (code.length > 1_000_000) throw new Error('literal input limit');
  return literal(parseExpression(code));
}
