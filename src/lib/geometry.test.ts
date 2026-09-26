import { describe, expect, it } from 'vitest'
import { basicToRay, rayToBasic, viewFromSamples } from './geometry'

describe('panorama camera coordinates', () => {
  it('round trips viewpoints including near the seam', () => {
    for (const point of [[.5,.5],[.001,.4],[.999,.6],[.2,.01]] as [number,number][]) {
      const actual = rayToBasic(basicToRay(point))
      expect(actual[0]).toBeCloseTo(point[0]); expect(actual[1]).toBeCloseTo(point[1])
    }
  })
  it('reconstructs a perspective basis from quarter-screen samples', () => {
    const u = .5 + Math.atan(.5)/(2*Math.PI), v = .5 + Math.atan(.5)/Math.PI
    const camera = viewFromSamples([.5,.5],[u,.5],[.5,v],1)
    expect(camera.origin).toEqual([0,0,1])
    expect(camera.right[0]).toBeCloseTo(1); expect(camera.down[1]).toBeCloseTo(-1)
  })
})
