import { render, screen } from "@testing-library/react";
import { ConfidenceView } from "./components/ConfidenceView";

test("shows reliable label at >=0.9 confidence and marks selected tool", () => {
  render(<ConfidenceView scores={{ rollback_deployment: 0.95, scale_out_service: 0.03 }}
    selected="rollback_deployment" confidence={0.95} />);
  expect(screen.getByText(/reliable/)).toBeTruthy();
  expect(screen.getByText("rollback_deployment")).toBeTruthy();
});

test("shows confirm/escalate label below 0.9", () => {
  render(<ConfidenceView scores={{ investigate_further: 0.4 }} selected="investigate_further" confidence={0.4} />);
  expect(screen.getByText(/confirm\/escalate/)).toBeTruthy();
});
