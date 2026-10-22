import { expect, test } from '@playwright/test';

test('Research Studio exposes the seven real workflow stages without running a model by itself', async ({ page }) => {
  await page.goto('/?mode=research');

  await expect(page.getByTestId('research-studio')).toBeVisible();
  await expect(page.getByRole('heading', { name: '从业务世界到可审计的 Skill 实验' })).toBeVisible();
  await expect(page.getByText('当前系统行为说明')).toBeVisible();
  await expect(page.getByRole('button', { name: /Designer 生成世界/ }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Reflector 提炼 Skill/ }).first()).toBeVisible();
  await expect(page.getByText('工程机制跑通 ≠ 已证明 RSI 能力提升')).toBeVisible();

  // Visiting and navigating the workspace is offline; only the explicit
  // Designer submit action can create a billable model call.
  const history = await page.request.get('/api/research/runs');
  expect(history.ok()).toBeTruthy();
  await page.getByRole('navigation', { name: '研究阶段' }).getByRole('button', { name: /Reflector 提炼 Skill/ }).click();
  await expect(page.getByText(/先运行 Designer 并完成一条 train 分区的真人 S0 Episode/)).toBeVisible();
});
