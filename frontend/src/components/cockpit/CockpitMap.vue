<template>
  <div class="cockpit-map">
    <!-- 有 Key：正常地图 -->
    <template v-if="hasKey">
      <div class="map-toolbar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索地点..."
          clearable
          class="map-search"
          @keyup.enter="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <el-button
          circle
          type="primary"
          :loading="locating"
          title="定位我的位置"
          @click="locateMe"
        >
          <el-icon v-if="!locating"><Aim /></el-icon>
        </el-button>

        <div v-if="location" class="loc-badge">
          <el-icon><LocationInformation /></el-icon>
          {{ location.city || '定位中...' }}
        </div>
      </div>
      <div ref="mapEl" class="map-canvas"></div>
      <div v-if="routeInfo" class="route-info">
        📍 {{ routeInfo.distance }} · ⏱ {{ routeInfo.time }}
      </div>
    </template>

    <!-- 无 Key：降级占位 -->
    <div v-else class="map-placeholder">
      <el-icon :size="48"><MapLocation /></el-icon>
      <p>未配置高德地图 Key</p>
      <p class="hint">在 <code>.env.local</code> 里设置 <code>VITE_AMAP_KEY</code> 后重启前端</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, LocationInformation, MapLocation, Aim } from '@element-plus/icons-vue'
import { useAmapLoader, hasAmapKey } from '@/composables/useAmapLoader'
import request from '@/api/request'

// 对外暴露当前城市（adcode + 名称），供天气卡等兄弟组件联动
const emit = defineEmits<{
  (e: 'city-change', payload: { adcode: string; city: string }): void
}>()

const hasKey = hasAmapKey()
const mapEl = ref<HTMLDivElement | null>(null)
const searchKeyword = ref('')
const location = ref<{ city: string; adcode: string; center: [number, number] } | null>(null)
const routeInfo = ref<{ distance: string; time: string } | null>(null)
const locating = ref(false)

// ⚠️ shallowRef 避免 Vue 深度追踪 AMap 内部对象（性能 + 内部循环引用报错）
const map = shallowRef<any>(null)
const autoComplete = shallowRef<any>(null)
const driving = shallowRef<any>(null)
let currentMarker: any = null
let AMapRef: any = null

onMounted(async () => {
  if (!hasKey) return

  try {
    // 1. 加载 SDK + 插件
    const AMap = await useAmapLoader([
      'AMap.AutoComplete',
      'AMap.PlaceSearch',
      'AMap.Driving',
    ])
    AMapRef = AMap

    // 2. 自动定位（走后端代理，IP 级别，仅用于初始中心点）
    let center: [number, number] = [116.404, 39.915]  // 默认北京
    try {
      const res: any = await request.get('/amap/locate')
      const data = res.data
      if (data?.center) {
        center = data.center
        location.value = {
          city: data.city,
          adcode: data.adcode || '110000',
          center,
        }
        emit('city-change', { adcode: data.adcode || '110000', city: data.city })
      }
    } catch {
      // 定位失败保持默认
    }

    // 3. 创建地图
    map.value = new AMap.Map(mapEl.value!, {
      zoom: 14,
      center,
      mapStyle: 'amap://styles/dark',
      viewMode: '2D',
    })

    // 起点标记
    currentMarker = new AMap.Marker({
      position: center,
      map: map.value,
      icon: new AMap.Icon({
        size: new AMap.Size(28, 34),
        image: '//webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
        imageSize: new AMap.Size(28, 34),
      }),
    })

    // 4. 搜索：AutoComplete -> PlaceSearch -> 定位到地点 -> 规划路线
    autoComplete.value = new AMap.AutoComplete({ city: '全国' })
    driving.value = new AMap.Driving({
      map: map.value,
      hideMarkers: false,
      policy: (AMap as any).DrivingPolicy?.LEAST_TIME,
    })

    // 5. 自动精确定位（浏览器 GPS/WiFi），静默执行不弹提示
    locateMe(true)

  } catch (e: any) {
    ElMessage.error(`地图加载失败：${e.message}`)
  }
})

/**
 * 浏览器精确定位：调用 Geolocation API 获取当前设备 GPS/WiFi 坐标
 * 成功后移动地图中心、更新起点 Marker、刷新 location
 */
function locateMe(silent = false) {
  if (!navigator.geolocation) {
    if (!silent) ElMessage.warning('当前浏览器不支持定位功能')
    return
  }
  if (!map.value || !AMapRef) {
    if (!silent) ElMessage.warning('地图尚未加载完成')
    return
  }

  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      locating.value = false
      const center: [number, number] = [pos.coords.longitude, pos.coords.latitude]

      // 移动地图中心 + 放大
      map.value.setZoomAndCenter(16, center)

      // 更新起点 Marker
      if (currentMarker) {
        currentMarker.setPosition(center)
      }

      // 更新位置信息（逆地理编码获取城市名）
      location.value = { city: '我的位置', adcode: '', center }
      reverseGeocode(center)

      if (!silent) ElMessage.success('已定位到你的位置')
    },
    (err) => {
      locating.value = false
      const tips: Record<number, string> = {
        1: '定位被拒绝，请在浏览器设置中允许位置权限',
        2: '位置不可用（可能未开启 GPS 或 WiFi）',
        3: '定位超时，请重试',
      }
      // 静默模式下定位失败不弹框，保留 IP 定位的初始结果
      if (!silent) ElMessage.error(tips[err.code] || `定位失败：${err.message}`)
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
  )
}

/**
 * 逆地理编码：经纬度 -> 城市名
 * 用高德 AMap.Geocoder 插件把坐标转成可读地址
 */
async function reverseGeocode(center: [number, number]) {
  try {
    const AMap = await useAmapLoader(['AMap.Geocoder'])
    const geocoder = new AMap.Geocoder()
    geocoder.getAddress(center, (status: string, result: any) => {
      if (status === 'complete' && result.regeocode) {
        const addr = result.regeocode.addressComponent
        const city = addr.city || addr.province || '当前位置'
        const adcode = addr.adcode || ''
        location.value = { city, adcode, center }
        if (adcode) emit('city-change', { adcode, city })
      }
    })
  } catch {
    // 逆地理失败不影响定位本身
  }
}

async function handleSearch() {
  if (!searchKeyword.value || !autoComplete.value || !map.value) return
  autoComplete.value.search(searchKeyword.value, (status: string, result: any) => {
    if (status !== 'complete' || !result.tips?.length) {
      ElMessage.warning('未找到相关地点')
      return
    }
    // 取第一个候选
    const tip = result.tips.find((t: any) => t.location)
    if (!tip) return
    const dest: [number, number] = [tip.location.lng, tip.location.lat]

    // 规划从当前位置到 dest 的驾车路线
    if (location.value && driving.value) {
      driving.value.clear()
      driving.value.search(
        location.value.center,
        dest,
        (s: string, res: any) => {
          if (s === 'complete' && res.routes?.length) {
            const r = res.routes[0]
            routeInfo.value = {
              distance: `${(r.distance / 1000).toFixed(1)} km`,
              time: `约 ${Math.round(r.time / 60)} 分钟`,
            }
          } else {
            ElMessage.warning('无法规划路线')
          }
        },
      )
    } else {
      // 没有起点，只定位到目的地
      map.value.setCenter(dest)
    }
  })
}

onBeforeUnmount(() => {
  driving.value?.clear()
  map.value?.destroy()
})
</script>

<style scoped>
.cockpit-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 320px;
  border-radius: 12px;
  overflow: hidden;
  background: var(--ck-bg-panel);
  border: 1px solid var(--ck-border);
}
.map-toolbar {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
}
.map-search {
  width: 300px;
}
.loc-badge {
  background: rgba(19, 26, 53, 0.85);
  color: var(--ck-text-primary);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--ck-border);
}
.map-canvas {
  width: 100%;
  height: 100%;
}
.route-info {
  position: absolute;
  left: 12px;
  bottom: 12px;
  background: rgba(19, 26, 53, 0.9);
  color: var(--ck-text-primary);
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--ck-border);
  font-size: 14px;
  z-index: 10;
}
.map-placeholder {
  height: 100%;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--ck-text-secondary);
}
.map-placeholder .hint {
  font-size: 12px;
}
.map-placeholder code {
  background: var(--ck-bg-elevated);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--ck-accent);
}
</style>