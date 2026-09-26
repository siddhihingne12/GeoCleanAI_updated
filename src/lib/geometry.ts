import type { Point, Vec3, ViewSpec } from '../types'

// Mapillary basic coordinates: top-left [0,0], bottom-right [1,1].
// A camera basis sampled from the viewer avoids compass/roll calibration errors.
export function basicToRay([u, v]: Point): Vec3 {
  const longitude = (u - .5) * 2 * Math.PI, latitude = (.5 - v) * Math.PI
  return [Math.cos(latitude) * Math.sin(longitude), Math.sin(latitude), Math.cos(latitude) * Math.cos(longitude)]
}
export function rayToBasic([x, y, z]: Vec3): Point {
  const norm = Math.hypot(x, y, z)
  return [((Math.atan2(x, z) / (2 * Math.PI) + .5) % 1 + 1) % 1, .5 - Math.asin(Math.max(-1, Math.min(1, y / norm))) / Math.PI]
}
const dot = (a: Vec3, b: Vec3) => a.reduce((s, v, i) => s + v * b[i], 0)
export function viewFromSamples(center: Point, right: Point, down: Point, aspect: number): ViewSpec {
  const origin = basicToRay(center)
  const tangent = (point: Point): Vec3 => {
    const ray = basicToRay(point), scale = dot(ray, origin)
    if (scale <= .05) throw new Error('Zoom in slightly before scanning this view.')
    // Samples are at 75% of viewport width/height: halfway from centre to edge.
    return ray.map((v, i) => 2 * (v / scale - origin[i])) as Vec3
  }
  return { origin, right: tangent(right), down: tangent(down), aspect }
}
