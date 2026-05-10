export interface ReportData {
  html_content: string;
  email_sent?: boolean;
  send_status?: string;
  sent_at: string;
}

export interface ResendResponse {
  success: boolean;
}
