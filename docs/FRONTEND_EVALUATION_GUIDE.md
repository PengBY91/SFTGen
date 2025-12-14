# 前端UI集成指南

## 概述

本文档说明如何在前端添加评测集功能的UI支持。后端API已完成，前端需要添加以下功能：

1. 任务创建时的评测配置
2. 任务详情页的评测集展示
3. 评测集下载功能

## 已完成的工作

### API模块
已创建 `frontend/src/api/evaluation.js`，包含三个API方法：
- `getEvaluationDataset(taskId)` - 获取评测集
- `getEvaluationStats(taskId)` - 获取统计信息
- `downloadEvaluation(taskId, format)` - 下载评测集

### 后端API端点
- `GET /api/tasks/{task_id}/evaluation` - 获取评测集数据
- `GET /api/tasks/{task_id}/evaluation/stats` - 获取统计信息
- `GET /api/tasks/{task_id}/evaluation/download` - 下载评测集

## 待实现的前端UI

### 1. 任务创建页面 (TaskCreate.vue)

在任务配置表单中添加评测集配置选项：

```vue
<template>
  <!-- 现有的任务配置表单 -->
  
  <!-- 新增：评测集配置 -->
  <a-collapse>
    <a-collapse-panel key="evaluation" header="评测集配置（可选）">
      <a-form-item label="启用评测集生成">
        <a-switch v-model:checked="config.evaluation_enabled" />
      </a-form-item>
      
      <template v-if="config.evaluation_enabled">
        <a-form-item label="评测集名称">
          <a-input v-model:value="config.evaluation_dataset_name" />
        </a-form-item>
        
        <a-form-item label="目标评测项数量">
          <a-input-number 
            v-model:value="config.evaluation_target_items" 
            :min="10" 
            :max="1000" 
          />
        </a-form-item>
        
        <a-form-item label="评测类型分布">
          <a-row :gutter="16">
            <a-col :span="6">
              <a-input-number 
                v-model:value="config.evaluation_type_distribution.knowledge_coverage"
                :min="0" 
                :max="1" 
                :step="0.1"
                addon-before="知识覆盖"
              />
            </a-col>
            <a-col :span="6">
              <a-input-number 
                v-model:value="config.evaluation_type_distribution.reasoning_ability"
                :min="0" 
                :max="1" 
                :step="0.1"
                addon-before="推理能力"
              />
            </a-col>
            <a-col :span="6">
              <a-input-number 
                v-model:value="config.evaluation_type_distribution.factual_accuracy"
                :min="0" 
                :max="1" 
                :step="0.1"
                addon-before="事实准确"
              />
            </a-col>
            <a-col :span="6">
              <a-input-number 
                v-model:value="config.evaluation_type_distribution.comprehensive"
                :min="0" 
                :max="1" 
                :step="0.1"
                addon-before="综合应用"
              />
            </a-col>
          </a-row>
        </a-form-item>
        
        <a-form-item label="难度分布">
          <a-row :gutter="16">
            <a-col :span="8">
              <a-input-number 
                v-model:value="config.evaluation_difficulty_distribution.easy"
                :min="0" 
                :max="1" 
                :step="0.1"
                addon-before="简单"
              />
            </a-col>
            <a-col :span="8">
              <a-input-number 
                v-model:value="config.evaluation_difficulty_distribution.medium"
                :min="0" 
                :max="1" 
                :step="0.1"
                addon-before="中等"
              />
            </a-col>
            <a-col :span="8">
              <a-input-number 
                v-model:value="config.evaluation_difficulty_distribution.hard"
                :min="0" 
                :max="1" 
                :step="0.1"
                addon-before="困难"
              />
            </a-col>
          </a-row>
        </a-form-item>
      </template>
    </a-collapse-panel>
  </a-collapse>
</template>

<script setup>
import { ref } from 'vue'

const config = ref({
  // 现有配置...
  
  // 评测集配置
  evaluation_enabled: false,
  evaluation_dataset_name: 'Domain Knowledge Evaluation Dataset',
  evaluation_target_items: 200,
  evaluation_type_distribution: {
    knowledge_coverage: 0.3,
    reasoning_ability: 0.3,
    factual_accuracy: 0.2,
    comprehensive: 0.2
  },
  evaluation_difficulty_distribution: {
    easy: 0.3,
    medium: 0.5,
    hard: 0.2
  },
  evaluation_output_format: 'benchmark',
  evaluation_min_quality_score: 0.5
})
</script>
```

### 2. 任务详情页面 (TaskDetail.vue)

添加评测集标签页：

```vue
<template>
  <a-tabs v-model:activeKey="activeTab">
    <!-- 现有标签页 -->
    <a-tab-pane key="output" tab="输出数据">
      <!-- 现有内容 -->
    </a-tab-pane>
    
    <!-- 新增：评测集标签页 -->
    <a-tab-pane key="evaluation" tab="评测集">
      <div v-if="evaluationLoading">
        <a-spin />
      </div>
      
      <div v-else-if="evaluationData">
        <!-- 统计信息卡片 -->
        <a-card title="评测集统计" class="mb-4">
          <a-descriptions :column="2">
            <a-descriptions-item label="总评测项">
              {{ evaluationStats.total_items }}
            </a-descriptions-item>
            <a-descriptions-item label="生成时间">
              {{ evaluationStats.generated_at || '未知' }}
            </a-descriptions-item>
          </a-descriptions>
          
          <!-- 类型分布图表 -->
          <div class="mt-4">
            <h4>评测类型分布</h4>
            <a-progress 
              v-for="(value, key) in evaluationStats.type_distribution" 
              :key="key"
              :percent="Math.round(value * 100)"
              :format="percent => `${getTypeName(key)}: ${percent}%`"
            />
          </div>
          
          <!-- 难度分布图表 -->
          <div class="mt-4">
            <h4>难度分布</h4>
            <a-progress 
              v-for="(value, key) in evaluationStats.difficulty_distribution" 
              :key="key"
              :percent="Math.round(value * 100)"
              :format="percent => `${getDifficultyName(key)}: ${percent}%`"
              :stroke-color="getDifficultyColor(key)"
            />
          </div>
        </a-card>
        
        <!-- 评测项列表 -->
        <a-card title="评测项预览">
          <a-table 
            :dataSource="evaluationData.items.slice(0, 10)" 
            :columns="evaluationColumns"
            :pagination="{ pageSize: 10 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'question'">
                <a-tooltip :title="record.question">
                  {{ record.question.substring(0, 50) }}...
                </a-tooltip>
              </template>
              <template v-if="column.key === 'type'">
                <a-tag>{{ getTypeName(record.type) }}</a-tag>
              </template>
              <template v-if="column.key === 'difficulty'">
                <a-tag :color="getDifficultyColor(record.difficulty)">
                  {{ getDifficultyName(record.difficulty) }}
                </a-tag>
              </template>
            </template>
          </a-table>
          
          <!-- 下载按钮 -->
          <div class="mt-4">
            <a-space>
              <a-button type="primary" @click="downloadEvaluation('json')">
                <DownloadOutlined /> 下载JSON格式
              </a-button>
              <a-button @click="viewFullData">
                <EyeOutlined /> 查看完整数据
              </a-button>
            </a-space>
          </div>
        </a-card>
      </div>
      
      <a-empty v-else description="该任务未生成评测集" />
    </a-tab-pane>
  </a-tabs>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getEvaluationDataset, getEvaluationStats, downloadEvaluation } from '@/api/evaluation'
import { DownloadOutlined, EyeOutlined } from '@ant-design/icons-vue'

const evaluationData = ref(null)
const evaluationStats = ref({})
const evaluationLoading = ref(false)

const evaluationColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 150 },
  { title: '问题', dataIndex: 'question', key: 'question' },
  { title: '类型', dataIndex: 'type', key: 'type', width: 120 },
  { title: '难度', dataIndex: 'difficulty', key: 'difficulty', width: 100 },
]

const loadEvaluationData = async () => {
  evaluationLoading.value = true
  try {
    const [dataRes, statsRes] = await Promise.all([
      getEvaluationDataset(taskId.value),
      getEvaluationStats(taskId.value)
    ])
    
    if (dataRes.success) {
      evaluationData.value = dataRes.data
    }
    if (statsRes.success) {
      evaluationStats.value = statsRes.data
    }
  } catch (error) {
    console.error('加载评测集失败:', error)
  } finally {
    evaluationLoading.value = false
  }
}

const getTypeName = (type) => {
  const names = {
    knowledge_coverage: '知识覆盖',
    reasoning_ability: '推理能力',
    factual_accuracy: '事实准确',
    comprehensive: '综合应用'
  }
  return names[type] || type
}

const getDifficultyName = (difficulty) => {
  const names = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return names[difficulty] || difficulty
}

const getDifficultyColor = (difficulty) => {
  const colors = {
    easy: 'green',
    medium: 'orange',
    hard: 'red'
  }
  return colors[difficulty] || 'default'
}

const handleDownloadEvaluation = async (format) => {
  try {
    const response = await downloadEvaluation(taskId.value, format)
    // 处理下载
    const url = window.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${taskId.value}_evaluation.${format}`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    console.error('下载失败:', error)
  }
}

onMounted(() => {
  if (activeTab.value === 'evaluation') {
    loadEvaluationData()
  }
})
</script>
```

## 实现步骤

1. **添加API模块**（已完成）
   - ✅ 创建 `frontend/src/api/evaluation.js`

2. **修改任务创建页面**
   - 在 `frontend/src/views/TaskCreate.vue` 中添加评测配置表单
   - 添加表单验证（确保分布总和为1.0）
   - 将评测配置包含在任务启动请求中

3. **修改任务详情页面**
   - 在 `frontend/src/views/TaskDetail.vue` 中添加评测集标签页
   - 实现评测数据加载和展示
   - 添加统计图表（可使用ECharts或Ant Design Charts）
   - 实现下载功能

4. **测试**
   - 创建任务时启用评测集
   - 验证评测集生成
   - 验证前端展示
   - 测试下载功能

## 注意事项

1. **分布验证**：确保类型分布和难度分布的总和为1.0
2. **错误处理**：妥善处理评测集不存在的情况
3. **加载状态**：显示适当的加载动画
4. **响应式设计**：确保在不同屏幕尺寸下正常显示

## 简化实现（可选）

如果时间有限，可以先实现基本功能：

1. **最小化配置**：只提供启用/禁用开关，使用默认配置
2. **简单展示**：只显示统计信息和下载按钮，不展示详细列表
3. **后续优化**：根据用户反馈逐步完善UI

## 总结

前端UI集成主要包括两部分：
- ✅ API调用层（已完成）
- ⏳ UI组件层（待实现，本文档提供了详细的实现指南）

后端API已完全就绪，前端开发人员可以根据本指南快速实现UI功能。
