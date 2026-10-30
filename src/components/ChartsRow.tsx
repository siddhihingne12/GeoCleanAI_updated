import { PieChart, Pie, Cell, AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { DashboardStats } from '../types'

const SEVERITY_COLORS = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' }

interface Props {
  stats: DashboardStats
  modelData: { model: string; count: number }[]
}

export function ChartsRow({ stats, modelData }: Props) {
  const severityData = [
    { name: 'High', value: stats.severity_distribution.high, color: SEVERITY_COLORS.high },
    { name: 'Medium', value: stats.severity_distribution.medium, color: SEVERITY_COLORS.medium },
    { name: 'Low', value: stats.severity_distribution.low, color: SEVERITY_COLORS.low },
  ].filter(d => d.value > 0)

  const dailyData = stats.daily_counts.map(d => ({ date: d.date.slice(5), count: d.count }))

  const barColors = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6']

  return (
    <div className="charts-row">
      {/* Severity Distribution */}
      <div className="chart-card">
        <h3 className="chart-title">Severity Distribution</h3>
        {severityData.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={severityData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" stroke="none">
                {severityData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        ) : <div className="chart-empty">No data yet</div>}
        <div className="chart-legend">
          {Object.entries(SEVERITY_COLORS).map(([level, color]) => (
            <span key={level}><span className="legend-dot" style={{ background: color }} />{level}: {stats.severity_distribution[level as keyof typeof stats.severity_distribution]}</span>
          ))}
        </div>
      </div>

      {/* Daily Trend */}
      <div className="chart-card">
        <h3 className="chart-title">Detection Trend (30 days)</h3>
        {dailyData.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={dailyData}>
              <defs>
                <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 9 }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 11 }} />
              <Area type="monotone" dataKey="count" stroke="#10b981" strokeWidth={2} fill="url(#greenGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : <div className="chart-empty">Scan panoramas to see trend data</div>}
      </div>

      {/* Model Comparison */}
      <div className="chart-card">
        <h3 className="chart-title">AI Model Usage</h3>
        {modelData.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={modelData} layout="vertical">
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="model" tick={{ fill: '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 11 }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {modelData.map((_, i) => <Cell key={i} fill={barColors[i % barColors.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : <div className="chart-empty">No model data yet</div>}
      </div>
    </div>
  )
}

