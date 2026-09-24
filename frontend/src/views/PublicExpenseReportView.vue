<template>
  <div class="expense-report-page">
    <div class="hero-card">
      <div>
        <p class="eyebrow">公共经费支出分析</p>
        <h1>公共经费月度报表</h1>
        <p class="hero-note">统计已支付及后续状态的公共经费采购记录；合并单按原申请人子单归属统计，避免重复计算。</p>
      </div>
      <div class="hero-actions">
        <el-select v-model="selectedYear" class="year-select" @change="handleYearChange">
          <el-option v-for="year in yearOptions" :key="year" :label="`${year} 年`" :value="year" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="fetchReport">刷新数据</el-button>
      </div>
    </div>

    <el-row :gutter="18" class="summary-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="metric-card total-card">
          <span>累计总支出</span>
          <strong>{{ formatMoney(report.summary.overall_total_amount) }}</strong>
          <small>所有年份实时累计</small>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="metric-card">
          <span>{{ report.year }} 年筛选支出</span>
          <strong>{{ formatMoney(report.summary.selected_year_total_amount) }}</strong>
          <small>{{ report.summary.selected_year_request_count }} 条采购记录</small>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="metric-card">
          <span>本月实时支出</span>
          <strong>{{ formatMoney(report.summary.current_month_total_amount) }}</strong>
          <small>按当前自然月统计</small>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="never" class="metric-card">
          <span>涉及人员 / 导师</span>
          <strong>{{ report.summary.person_count }} / {{ report.summary.tutor_count }}</strong>
          <small>当前筛选范围</small>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="月份">
          <el-select v-model="filters.month" clearable placeholder="全部月份" class="filter-select" @change="fetchReport">
            <el-option v-for="month in monthOptions" :key="month.value" :label="month.label" :value="month.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="导师">
          <el-select v-model="filters.tutor_id" clearable filterable placeholder="全部导师" class="filter-select" @change="fetchReport">
            <el-option v-for="tutor in tutorOptions" :key="tutor.id" :label="tutor.name" :value="tutor.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="申请人">
          <el-select v-model="filters.applicant_id" clearable filterable placeholder="全部申请人" class="filter-select" @change="fetchReport">
            <el-option v-for="applicant in applicantOptions" :key="applicant.id" :label="applicant.name" :value="applicant.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置筛选</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card" v-loading="loading">
      <template #header>
        <div class="panel-header">
          <div>
            <h2>月度支出趋势</h2>
            <p>{{ report.year }} 年每月公共经费采购花费</p>
          </div>
          <el-tag type="info" effect="plain">月度报表</el-tag>
        </div>
      </template>

      <div class="month-chart" v-if="monthChartRows.length">
        <div v-for="month in monthChartRows" :key="month.month" class="month-column">
          <div class="amount-label">{{ compactMoney(month.amount) }}</div>
          <div class="bar-track">
            <div class="bar-fill" :style="{ height: `${month.percent}%` }"></div>
          </div>
          <div class="month-label">{{ month.label }}</div>
          <div class="count-label">{{ month.count }} 条</div>
        </div>
      </div>
      <el-empty v-else description="当前年度暂无支出数据" />
    </el-card>

    <el-row :gutter="18" class="content-row">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="panel-card person-panel" v-loading="loading">
          <template #header>
            <div class="panel-header">
              <div>
                <h2>个人支出排行</h2>
                <p>显示每个人花费金额及其对应导师</p>
              </div>
              <el-tag type="success" effect="plain">{{ report.people.length }} 人</el-tag>
            </div>
          </template>

          <div class="ranking-chart" v-if="topPeopleRows.length">
            <div v-for="person in topPeopleRows" :key="person.applicant_id" class="rank-row">
              <div class="rank-name">
                <strong>{{ person.applicant_name }}</strong>
                <span>{{ person.tutor_name }}</span>
              </div>
              <div class="rank-bar-wrap">
                <div class="rank-bar" :style="{ width: `${person.percent}%` }"></div>
              </div>
              <div class="rank-money">{{ formatMoney(person.total_amount) }}</div>
            </div>
          </div>
          <el-empty v-else description="暂无个人支出数据" />

          <el-table :data="report.people" border stripe class="detail-table" max-height="420">
            <el-table-column prop="rank" label="#" width="70" align="center" />
            <el-table-column prop="applicant_name" label="申请人" min-width="120" />
            <el-table-column prop="tutor_name" label="对应导师" min-width="120" />
            <el-table-column prop="request_count" label="记录数" width="90" align="center" sortable />
            <el-table-column label="累计金额" min-width="140" sortable :sort-method="sortByAmount">
              <template #default="scope">{{ formatMoney(scope.row.total_amount) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="panel-card tutor-panel" v-loading="loading">
          <template #header>
            <div class="panel-header">
              <div>
                <h2>导师累计金额</h2>
                <p>按学生对应导师汇总公共经费花费</p>
              </div>
              <el-tag type="warning" effect="plain">{{ report.tutors.length }} 位</el-tag>
            </div>
          </template>

          <div v-if="tutorRows.length" class="tutor-list">
            <div v-for="tutor in tutorRows" :key="tutor.tutor_id || tutor.tutor_name" class="tutor-card">
              <div class="tutor-topline">
                <strong>{{ tutor.tutor_name }}</strong>
                <span>{{ formatMoney(tutor.total_amount) }}</span>
              </div>
              <div class="tutor-meta">
                <span>{{ tutor.student_count }} 名学生</span>
                <span>{{ tutor.request_count }} 条记录</span>
              </div>
              <el-progress :percentage="tutor.percent" :show-text="false" :stroke-width="10" />
            </div>
          </div>
          <el-empty v-else description="暂无导师统计数据" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import apiClient from '@/api';

const currentYear = new Date().getFullYear();
const loading = ref(false);
const selectedYear = ref(currentYear);

const report = reactive({
  year: currentYear,
  available_years: [currentYear],
  summary: {
    overall_total_amount: '0.00',
    selected_year_total_amount: '0.00',
    selected_year_request_count: 0,
    current_month_total_amount: '0.00',
    person_count: 0,
    tutor_count: 0,
  },
  monthly: [],
  people: [],
  tutors: [],
  filter_options: {
    months: [],
    applicants: [],
    tutors: [],
  },
});

const filters = reactive({
  month: null,
  applicant_id: null,
  tutor_id: null,
});

const numberValue = (value) => Number(value || 0);

const formatMoney = (value) => new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  minimumFractionDigits: 2,
}).format(numberValue(value));

const compactMoney = (value) => {
  const amount = numberValue(value);
  if (amount >= 10000) return `${(amount / 10000).toFixed(1)}万`;
  if (amount >= 1000) return `${(amount / 1000).toFixed(1)}k`;
  return amount.toFixed(0);
};

const yearOptions = computed(() => {
  const years = new Set(report.available_years.length ? report.available_years : [currentYear]);
  years.add(currentYear);
  return Array.from(years).sort((a, b) => b - a);
});

const monthOptions = computed(() => report.filter_options.months || []);
const applicantOptions = computed(() => report.filter_options.applicants || []);
const tutorOptions = computed(() => report.filter_options.tutors || []);

const monthChartRows = computed(() => {
  const maxAmount = Math.max(...report.monthly.map(item => numberValue(item.amount)), 0);
  return report.monthly.map(item => ({
    ...item,
    percent: maxAmount > 0 ? Math.max((numberValue(item.amount) / maxAmount) * 100, item.count > 0 ? 8 : 0) : 0,
  }));
});

const topPeopleRows = computed(() => {
  const topRows = report.people.slice(0, 10);
  const maxAmount = Math.max(...topRows.map(item => numberValue(item.total_amount)), 0);
  return topRows.map(item => ({
    ...item,
    percent: maxAmount > 0 ? Math.max((numberValue(item.total_amount) / maxAmount) * 100, 6) : 0,
  }));
});

const tutorRows = computed(() => {
  const maxAmount = Math.max(...report.tutors.map(item => numberValue(item.total_amount)), 0);
  return report.tutors.map(item => ({
    ...item,
    percent: maxAmount > 0 ? Math.round((numberValue(item.total_amount) / maxAmount) * 100) : 0,
  }));
});

const sortByAmount = (a, b) => numberValue(a.total_amount) - numberValue(b.total_amount);

const buildRequestParams = () => {
  const params = { year: selectedYear.value };
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      params[key] = value;
    }
  });
  return params;
};

const fetchReport = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/procurement/public-expense-report/', {
      params: buildRequestParams(),
    });
    const data = response.data;
    report.year = data.year;
    report.available_years = data.available_years || [data.year || currentYear];
    Object.assign(report.summary, data.summary || {});
    report.monthly = data.monthly || [];
    report.people = data.people || [];
    report.tutors = data.tutors || [];
    report.filter_options = data.filter_options || { months: [], applicants: [], tutors: [] };
    selectedYear.value = report.year;
    if (data.filters) {
      filters.month = data.filters.month ?? null;
      filters.applicant_id = data.filters.applicant_id ?? null;
      filters.tutor_id = data.filters.tutor_id ?? null;
    }
  } catch (error) {
    const message = error.response?.data?.detail || error.response?.data?.message || '获取公共经费报表失败。';
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
};

const resetFilters = () => {
  filters.month = null;
  filters.applicant_id = null;
  filters.tutor_id = null;
  fetchReport();
};

const handleYearChange = () => {
  filters.month = null;
  filters.applicant_id = null;
  filters.tutor_id = null;
  fetchReport();
};

onMounted(fetchReport);
</script>

<style scoped>
.expense-report-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 28px;
  border-radius: 18px;
  background:
    radial-gradient(circle at 12% 20%, rgba(77, 124, 15, 0.18), transparent 30%),
    linear-gradient(135deg, #0f3d2e 0%, #14532d 46%, #365314 100%);
  color: #f7fee7;
  box-shadow: 0 16px 40px rgba(20, 83, 45, 0.18);
}

.eyebrow {
  margin: 0 0 8px;
  letter-spacing: 0.16em;
  font-size: 12px;
  color: #bef264;
}

.hero-card h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.2;
}

.hero-note {
  margin: 10px 0 0;
  max-width: 720px;
  color: #dcfce7;
}

.hero-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

.year-select {
  width: 140px;
}

.summary-row,
.content-row {
  row-gap: 18px;
}

.filter-card {
  border: none;
  border-radius: 16px;
}

.filter-card :deep(.el-card__body) {
  padding-bottom: 2px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}

.filter-select {
  width: 180px;
}

.metric-card {
  border: none;
  border-radius: 16px;
  background: #ffffff;
}

.metric-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 118px;
}

.metric-card span {
  color: #64748b;
  font-size: 14px;
}

.metric-card strong {
  color: #0f172a;
  font-size: 26px;
  line-height: 1.1;
}

.metric-card small {
  color: #94a3b8;
}

.total-card {
  background: linear-gradient(145deg, #f7fee7, #ffffff);
}

.panel-card {
  border: none;
  border-radius: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.panel-header h2 {
  margin: 0;
  font-size: 19px;
  color: #1f2937;
}

.panel-header p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.month-chart {
  display: grid;
  grid-template-columns: repeat(12, minmax(56px, 1fr));
  gap: 14px;
  min-height: 320px;
  align-items: end;
  overflow-x: auto;
  padding: 10px 4px 0;
}

.month-column {
  display: grid;
  grid-template-rows: 26px 220px 24px 20px;
  min-width: 56px;
  justify-items: center;
  color: #475569;
}

.amount-label,
.count-label {
  font-size: 12px;
  color: #64748b;
}

.month-label {
  font-weight: 700;
  color: #334155;
}

.bar-track {
  position: relative;
  width: 32px;
  height: 220px;
  border-radius: 999px;
  background: #ecfdf5;
  overflow: hidden;
  border: 1px solid #d9f99d;
}

.bar-fill {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  min-height: 0;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(180deg, #84cc16 0%, #16a34a 100%);
  transition: height 0.35s ease;
}

.ranking-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 18px;
}

.rank-row {
  display: grid;
  grid-template-columns: 150px 1fr 130px;
  gap: 12px;
  align-items: center;
}

.rank-name {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.rank-name strong {
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-name span {
  color: #64748b;
  font-size: 12px;
}

.rank-bar-wrap {
  height: 12px;
  border-radius: 999px;
  background: #eef2ff;
  overflow: hidden;
}

.rank-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2563eb, #14b8a6);
  transition: width 0.35s ease;
}

.rank-money {
  text-align: right;
  font-weight: 700;
  color: #0f172a;
}

.detail-table {
  margin-top: 10px;
}

.tutor-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tutor-card {
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.tutor-topline,
.tutor-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.tutor-topline strong {
  color: #111827;
  font-size: 16px;
}

.tutor-topline span {
  color: #166534;
  font-weight: 800;
}

.tutor-meta {
  margin: 8px 0 12px;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 900px) {
  .hero-card,
  .hero-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-card h1 {
    font-size: 26px;
  }

  .filter-select {
    width: 100%;
  }

  .filter-form :deep(.el-form-item) {
    width: 100%;
    margin-right: 0;
  }

  .month-chart {
    grid-template-columns: repeat(12, 64px);
  }

  .rank-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .rank-money {
    text-align: left;
  }
}
</style>
