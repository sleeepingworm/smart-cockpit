// frontend/src/composables/useAmapLoader.ts
import AMapLoader from '@amap/amap-jsapi-loader'

let _loaderPromise: Promise<any> | null = null

/**
 * 单例加载高德 JS API 2.0
 * @param plugins 需要的插件名，如 ['AMap.AutoComplete', 'AMap.Driving']
 */
export function useAmapLoader(plugins: string[] = []) {
  if (!_loaderPromise) {
    // 配置安全密钥（必须在 load 之前）
    ;(window as any)._AMapSecurityConfig = {
      securityJsCode: import.meta.env.VITE_AMAP_SECURITY || '',
    }

    _loaderPromise = AMapLoader.load({
      key: import.meta.env.VITE_AMAP_KEY || '',
      version: '2.0',
      plugins,
    })
  }
  return _loaderPromise
}

/**
 * Key 是否配置？供 UI 决定是否显示地图 or 占位符
 */
export function hasAmapKey(): boolean {
  return !!import.meta.env.VITE_AMAP_KEY
}