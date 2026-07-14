<template>
  <div class="sensor-card" :class="{ warning }">
    <div class="card-head">
      <span class="icon" :style="{ background: color + '22', color }">
        {{ icon }}
      </span>
      <span class="label">{{ label }}</span>
    </div>
    <div class="value">
      <span class="num">{{ displayValue }}</span>
      <span class="unit">{{ unit }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  icon: string
  label: string
  value: number | null | undefined
  unit: string
  color?: string
  warnThreshold?: number
}>()

const color = computed(() => props.color || '#4e7cff')
const displayValue = computed(() => (props.value == null ? '--' : props.value))
const warning = computed(() =>
  props.warnThreshold != null && props.value != null && props.value > props.warnThreshold,
)
</script>

<style scoped>
.sensor-card {
  padding: 16px;
  background: var(--ck-bg-panel);
  border: 1px solid var(--ck-border);
  border-radius: 10px;
  transition: border-color 0.2s, transform 0.2s;
}
.sensor-card:hover {
  border-color: var(--ck-accent);
  transform: translateY(-2px);
}
.sensor-card.warning {
  border-color: var(--ck-danger);
  box-shadow: 0 0 20px rgba(255, 107, 107, 0.15);
}
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ck-text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}
.icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.num {
  font-size: 32px;
  font-weight: 700;
  color: var(--ck-text-primary);
  line-height: 1;
}
.unit {
  color: var(--ck-text-secondary);
  font-size: 14px;
}
</style>