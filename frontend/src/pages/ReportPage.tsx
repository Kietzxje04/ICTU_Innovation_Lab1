import { ArrowLeft, BookOpen, Building2, CheckCircle2, Download, FileText, Printer, ShieldCheck } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { FINAL_STATUS_LABELS, NODE_LABELS } from '../domain'
import { useReadiness } from '../readiness-context'
import { useAuth } from '../auth-context'

const money = (value: number | null) => value === null ? 'Chưa cung cấp' : `${new Intl.NumberFormat('vi-VN').format(value)} VND`
const dateFormatter = new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

function downloadBlob(content: BlobPart[], type: string, filename: string) {
  const url = URL.createObjectURL(new Blob(content, { type }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function ReportPage() {
  const { caseId } = useParams()
  const { cases } = useReadiness()
  const { user } = useAuth()
  const item = cases.find((entry) => entry.id === caseId)
  if (!item) return <main className="page not-found"><h1>Không tìm thấy hồ sơ báo cáo</h1><Link className="primary-button" to="/">Về dashboard</Link></main>

  const { context, workflow } = item
  const missingDocuments = context.required_documents.filter((document) => !context.submitted_documents.includes(document))
  const issueArtifacts = workflow.route.map((node) => workflow.artifacts[node]).filter((artifact) => artifact && artifact.status !== 'PASS')
  const proposedActions = [...new Set(issueArtifacts.flatMap((artifact) => artifact.proposed_actions))]
  const warnings = [...new Set(issueArtifacts.flatMap((artifact) => artifact.warnings))]
  const reportDate = new Date()
  const responseDate = new Date(reportDate)
  responseDate.setDate(responseDate.getDate() + 5)

  const exportWord = () => {
    const report = document.getElementById('company-supplement-report')
    if (!report) return
    const wordStyles = `
      body{font-family:Arial,sans-serif;color:#17212b;font-size:11pt;line-height:1.5;margin:36px}
      h1{font-size:19pt;color:#064984} h2{font-size:13pt;color:#07549a;border-bottom:1px solid #ccd7df;padding-bottom:5px}
      table{width:100%;border-collapse:collapse;margin:10px 0 18px} th,td{border:1px solid #aebdc8;padding:7px;text-align:left;vertical-align:top} th{background:#eaf3fa}
      .report-letterhead{text-align:center}.report-letterhead h1{margin-bottom:4px}.report-letterhead p{margin:2px}.report-subject{margin:24px 0}.report-notice{padding:10px;background:#fff5e9;border-left:4px solid #ed7621}
      .report-source{margin:8px 0;padding:9px;background:#f3f6f8}.report-signature{margin-top:35px;text-align:right}.report-disclaimer{font-size:9pt;color:#657583;border-top:1px solid #ccd7df;padding-top:10px}
    `
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${item.id}</title><style>${wordStyles}</style></head><body>${report.innerHTML}</body></html>`
    downloadBlob(['\ufeff', html], 'application/msword;charset=utf-8', `${item.id}-yeu-cau-bo-sung.doc`)
  }

  return <main className="report-page">
    <div className="report-actions"><Link className="back-link" to={`/cases/${item.id}`}><ArrowLeft size={15} /> Quay lại hồ sơ</Link><div><span>Bản xem trước báo cáo gửi doanh nghiệp</span><button className="outline-button" onClick={exportWord}><Download size={14} /> Xuất Word (.doc)</button><button className="primary-button" onClick={() => window.print()}><Printer size={14} /> In / Lưu PDF</button></div></div>
    <article className="report-paper" id="company-supplement-report">
      <header className="report-letterhead"><div className="report-logo"><Building2 size={25} /></div><h1>NEXUSOPS AI — SME LOAN READINESS</h1><p>PHIẾU YÊU CẦU BỔ SUNG VÀ GIẢI TRÌNH HỒ SƠ</p><small>Số: {item.id}/RFR · Ngày {dateFormatter.format(reportDate)}</small></header>
      <section className="report-recipient"><p><strong>Kính gửi:</strong> {item.company_name}</p><p><strong>Mã khách hàng:</strong> {context.customer_id}</p><p><strong>Người phụ trách hồ sơ:</strong> {item.owner}</p><p className="report-handler-line"><strong>Người xử lý hồ sơ:</strong> {user?.full_name ?? item.owner}</p><p className="report-handler-line"><strong>Chức vụ:</strong> {user?.role_name ?? user?.role_id ?? 'Chuyên viên'}</p></section>
      <section className="report-subject"><strong>V/v: Thông báo kết quả kiểm chứng readiness và yêu cầu bổ sung thông tin</strong><p>Hệ thống đã hoàn tất quy trình kiểm chứng dữ liệu, tài liệu, chỉ số tài chính và căn cứ chính sách cho hồ sơ nêu trên. Kết quả này phục vụ cán bộ chuyên môn rà soát và không phải quyết định phê duyệt hoặc từ chối khoản vay.</p></section>
      <section className={`report-notice ${workflow.final_status === 'BLOCKED' ? 'blocked' : ''}`}><div><ShieldCheck size={19} /><span>Trạng thái sau kiểm chứng</span></div><strong>{FINAL_STATUS_LABELS[workflow.final_status]}</strong><p>Phản biện bắt buộc: {workflow.critic_verdict} · {workflow.route.length} khâu đã được thực hiện.</p></section>

      <section className="report-section"><h2>1. Thông tin khoản đề nghị</h2><table><tbody><tr><th>Sản phẩm</th><td>{context.product === 'WORKING_CAPITAL' ? 'Vốn lưu động' : 'Thấu chi doanh nghiệp'}</td><th>Số tiền đề nghị</th><td>{money(context.requested_amount)}</td></tr><tr><th>Doanh thu năm</th><td>{money(context.annual_revenue)}</td><th>Doanh thu khai thuế</th><td>{money(context.tax_declared_revenue)}</td></tr><tr><th>Thời gian quan hệ</th><td>{context.relationship_months} tháng</td><th>Chi nhánh tiếp nhận</th><td>{context.metadata.branch}</td></tr></tbody></table></section>

      <section className="report-section"><h2>2. Các vấn đề cần bổ sung hoặc giải trình</h2>{issueArtifacts.length ? <table><thead><tr><th>STT</th><th>Khâu kiểm chứng</th><th>Vấn đề được phát hiện</th><th>Mức xử lý</th></tr></thead><tbody>{issueArtifacts.map((artifact, index) => <tr key={artifact.agent_id}><td>{index + 1}</td><td>{NODE_LABELS[artifact.agent_id] ?? artifact.agent_id}</td><td>{artifact.summary}{artifact.warnings.length > 0 && <div className="report-warning-codes">Mã cảnh báo: {artifact.warnings.join(', ')}</div>}</td><td>{artifact.status === 'BLOCKED' ? 'Bắt buộc xử lý' : 'Cần rà soát'}</td></tr>)}</tbody></table> : <div className="report-success"><CheckCircle2 size={17} /> Không phát hiện vấn đề trọng yếu cần doanh nghiệp bổ sung.</div>}</section>

      <section className="report-section"><h2>3. Danh mục tài liệu còn thiếu</h2>{missingDocuments.length ? <table><thead><tr><th>STT</th><th>Tài liệu cần bổ sung</th><th>Yêu cầu phản hồi</th><th>Doanh nghiệp xác nhận</th></tr></thead><tbody>{missingDocuments.map((document, index) => <tr key={document}><td>{index + 1}</td><td>{document.replaceAll('_', ' ')}</td><td>Bản hợp lệ, còn hiệu lực và có thể đối chiếu</td><td>☐ Đã gửi &nbsp; ☐ Chưa gửi</td></tr>)}</tbody></table> : <div className="report-success"><CheckCircle2 size={17} /> Hồ sơ đã có đủ danh mục tài liệu bắt buộc theo workflow.</div>}</section>

      <section className="report-section"><h2>4. Hành động doanh nghiệp cần thực hiện</h2><ol className="report-action-list">{missingDocuments.length > 0 && <li>Bổ sung đầy đủ các tài liệu tại Mục 3.</li>}{warnings.includes('FINANCIAL_TAX_MISMATCH') && <li>Giải trình nguyên nhân chênh lệch giữa doanh thu báo cáo tài chính và doanh thu khai thuế; gửi bảng đối chiếu có xác nhận.</li>}{warnings.includes('NEGATIVE_PRETAX_PROFIT') && <li>Giải trình nguyên nhân lợi nhuận trước thuế âm và cung cấp kế hoạch khắc phục dòng tiền.</li>}{warnings.includes('CIC_BAD_DEBT') && <li>Cung cấp tài liệu giải trình tình trạng CIC và chứng từ hoàn thành nghĩa vụ liên quan, nếu có.</li>}{warnings.includes('LOW_ACCOUNT_TURNOVER') && <li>Giải trình vòng quay tài khoản thấp và cung cấp sao kê/dự báo dòng tiền bổ sung.</li>}{context.kyc_aml_flags.length > 0 && <li>Cung cấp thông tin xác minh chủ sở hữu hưởng lợi và hồ sơ KYC theo yêu cầu của cán bộ tuân thủ.</li>}{proposedActions.map((action) => <li key={action}>Thực hiện yêu cầu nghiệp vụ: {action.replaceAll('_', ' ')}.</li>)}{!missingDocuments.length && !warnings.length && !proposedActions.length && <li>Không yêu cầu bổ sung tại thời điểm lập báo cáo; vui lòng chờ cán bộ chuyên môn liên hệ.</li>}</ol><p className="report-deadline"><strong>Thời hạn đề nghị phản hồi:</strong> trước ngày {dateFormatter.format(responseDate)}.</p></section>

      <section className="report-section"><h2>5. Căn cứ và trích dẫn sử dụng</h2>{item.evidence.filter((evidence) => evidence.domain !== 'CASE_DATA').map((evidence, index) => <div className="report-source" key={evidence.chunk_id}><div><strong>{index + 1}. {evidence.document_title}</strong><span>{evidence.document_number} · {evidence.article ?? ''} {evidence.clause ?? ''} · Hiệu lực {evidence.effective_date}</span></div><blockquote>“{evidence.citation_text}”</blockquote><p><strong>Cơ sở áp dụng:</strong> {evidence.evaluation_basis}</p></div>)}</section>

      <section className="report-section"><h2>6. Phiếu phản hồi của doanh nghiệp</h2><table><tbody><tr><th>Nội dung phản hồi/giải trình</th><td className="report-writing-area" /></tr><tr><th>Danh sách tệp gửi kèm</th><td className="report-writing-area short" /></tr><tr><th>Người đại diện xác nhận</th><td>Họ tên: ........................................................ Chức vụ: ........................................................</td></tr><tr><th>Ngày xác nhận</th><td>........ / ........ / ........</td></tr></tbody></table></section>

      <footer><div className="report-signature"><strong>ĐẠI DIỆN ĐƠN VỊ TIẾP NHẬN</strong><span>(Ký, ghi rõ họ tên)</span></div><p className="report-disclaimer">Báo cáo được tạo từ NexusOps AI phục vụ quy trình loan readiness. Các phát hiện và đề xuất trong báo cáo cần được cán bộ có thẩm quyền kiểm tra trước khi gửi chính thức tới doanh nghiệp.</p></footer>
    </article>
  </main>
}
