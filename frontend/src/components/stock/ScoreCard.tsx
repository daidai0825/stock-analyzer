import type { StockScore } from '../../types/stock';

interface ScoreCardProps {
  score: StockScore;
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#eab308';
  return '#ef4444';
}

function getScoreLabel(score: number): string {
  if (score >= 80) return '優秀';
  if (score >= 60) return '良好';
  if (score >= 40) return '普通';
  return '偏低';
}

interface RingChartProps {
  score: number;
  size?: number;
}

function RingChart({ score, size = 100 }: RingChartProps) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = getScoreColor(score);
  const cx = size / 2;
  const cy = size / 2;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background ring */}
      <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#e5e7eb" strokeWidth="8" />
      {/* Progress ring */}
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeDasharray={`${progress} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
      />
      {/* Score text */}
      <text x={cx} y={cy - 6} textAnchor="middle" fontSize="20" fontWeight="bold" fill={color}>
        {score}
      </text>
      <text x={cx} y={cy + 12} textAnchor="middle" fontSize="9" fill="#6b7280">
        {getScoreLabel(score)}
      </text>
    </svg>
  );
}

interface ProgressBarProps {
  label: string;
  score: number;
}

function ProgressBar({ label, score }: ProgressBarProps) {
  const color = getScoreColor(score);
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold" style={{ color }}>
          {score}
        </span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div
          className="h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export function ScoreCard({ score }: ScoreCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">品質評分</h2>
      <div className="flex flex-col sm:flex-row gap-6">
        {/* Left: ring chart + grade */}
        <div className="flex flex-col items-center justify-center gap-2 min-w-[120px]">
          <RingChart score={score.overallScore} size={100} />
          <p className="text-xs text-gray-500">
            綜合評分
          </p>
          <span
            className="text-sm font-bold px-3 py-0.5 rounded-full"
            style={{
              backgroundColor: `${getScoreColor(score.overallScore)}20`,
              color: getScoreColor(score.overallScore),
            }}
          >
            品質等級：{score.grade}
          </span>
        </div>

        {/* Middle: dimension progress bars */}
        <div className="flex-1 flex flex-col justify-center">
          <ProgressBar label="估值" score={score.valuationScore} />
          <ProgressBar label="技術面" score={score.technicalScore} />
          <ProgressBar label="基本面" score={score.fundamentalScore} />
        </div>

        {/* Right: signals */}
        {score.signals.length > 0 && (
          <div className="flex-1 min-w-[160px]">
            <p className="text-xs font-semibold text-gray-500 mb-2">訊號</p>
            <ul className="space-y-1.5">
              {score.signals.map((signal, idx) => (
                <li key={idx} className="flex items-start gap-1.5 text-xs">
                  <span
                    className={`mt-0.5 shrink-0 w-1.5 h-1.5 rounded-full ${
                      signal.type === 'positive'
                        ? 'bg-green-500'
                        : signal.type === 'negative'
                          ? 'bg-red-500'
                          : 'bg-gray-400'
                    }`}
                  />
                  <span
                    className={
                      signal.type === 'positive'
                        ? 'text-green-700'
                        : signal.type === 'negative'
                          ? 'text-red-700'
                          : 'text-gray-500'
                    }
                  >
                    {signal.message}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
