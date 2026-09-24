<template>
  <div>
    <el-form :model="filters" inline class="controls-container">
        <el-form-item label="申请日期">
            <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" clearable unlink-panels />
        </el-form-item>
        <el-form-item label="申请人">
            <el-select v-model="filters.applicant" placeholder="选择申请人" clearable filterable>
            <el-option v-for="user in applicantOptions" :key="user.id" :label="user.name" :value="user.id" />
            </el-select>
        </el-form-item>
        <el-form-item label="采购人员">
            <el-select v-model="filters.handler" placeholder="选择采购人员" clearable filterable>
            <el-option v-for="user in procurementStaffOptions" :key="user.id" :label="user.name" :value="user.id" />
            </el-select>
        </el-form-item>
        <el-form-item label="金额排序">
            <el-select v-model="filters.amountSort" placeholder="请选择" clearable style="width: 160px;">
              <el-option label="金额升序" value="total_price" />
              <el-option label="金额降序" value="-total_price" />
            </el-select>
        </el-form-item>
        <el-form-item v-if="showInvoiceFilter" label="发票单号">
            <el-input v-model="filters.invoiceNumber" placeholder="请输入发票单号" clearable style="width: 200px;" @keyup.enter="applyFilters" />
        </el-form-item>
        <el-form-item>
            <el-input v-model="filters.searchQuery" placeholder="关键词搜索 (物品/单号等)" clearable @keyup.enter="applyFilters" style="width: 240px;">
            <template #append><el-button @click="applyFilters"><el-icon><Search /></el-icon></el-button></template>
            </el-input>
        </el-form-item>
        <el-form-item class="actions-item">
            <el-button type="primary" size="large" @click="applyFilters">筛选</el-button>
            <el-button size="large" @click="resetFilters">重置</el-button>
        </el-form-item>
    </el-form>

    <div class="selection-summary" v-if="!isPrintMode && selectedRequests.length > 0">
      已选合计金额：¥{{ selectedTotal }}
      <el-button type="primary" size="small" @click="showSelectedOnly = true">筛选已勾选条目</el-button>
    </div>

    <el-table :data="displayedRequests" stripe border style="width: 100%" row-key="id" ref="tableRef" @selection-change="handleSelectionChange" @expand-change="handleExpandChange">
      <el-table-column v-if="!isPrintMode" type="selection" width="55" align="center" :selectable="isRowSelectable" />
      <el-table-column type="expand">
        <template #default="props">
          <div v-loading="detailsState[props.row.id]?.isLoading" class="details-wrapper">
            <div v-if="detailsState[props.row.id]?.data" class="details-container">

              <template v-if="detailsState[props.row.id].data.merged_children && detailsState[props.row.id].data.merged_children.length > 0">
                <div>
                  <el-descriptions title="合并后总览" :column="4" border>
                    <el-descriptions-item label="申请人 (合并)">{{ detailsState[props.row.id].data.applicant.name }}</el-descriptions-item>
                    <el-descriptions-item label="单号" :span="3">{{ detailsState[props.row.id].data.order_number }}</el-descriptions-item>
                    <el-descriptions-item label="总金额" :span="4">¥{{ detailsState[props.row.id].data.total_price }}</el-descriptions-item>

                    <el-descriptions-item label="采购物品" :span="4">
                        <div v-for="(item, index) in detailsState[props.row.id].data.items" :key="item.id" class="item-block-nested">
                          <p class="item-title">
                            <strong>物品 {{ index + 1 }}: {{ item.content }}</strong>
                            <span style="font-size: 12px; color: #909399;"> (原始申请人: {{ item.original_applicant_name || 'N/A' }})</span>
                          </p>
                          <el-descriptions :column="3" border size="small">
                              <el-descriptions-item label="采购类型">{{ item.purchase_type || 'N/A' }}</el-descriptions-item>
                              <el-descriptions-item label="厂商">{{ item.manufacturer || 'N/A' }}</el-descriptions-item>
                              <el-descriptions-item label="CAS号">{{ item.cas_number || 'N/A' }}</el-descriptions-item>
                              <el-descriptions-item label="货号">{{ item.product_number || 'N/A' }}</el-descriptions-item>
                              <el-descriptions-item label="参数">{{ item.parameters || 'N/A' }}</el-descriptions-item>
                              <el-descriptions-item label="规格">{{ item.specifications || 'N/A' }}</el-descriptions-item>
                              <el-descriptions-item label="数量">{{ item.quantity }}</el-descriptions-item>
                              <el-descriptions-item label="单价">¥{{ item.unit_price }}</el-descriptions-item>
                              <el-descriptions-item label="采购链接">
                                  <el-link :href="item.purchase_link" type="primary" target="_blank" v-if="item.purchase_link">点击跳转</el-link>
                                  <span v-else>N/A</span>
                              </el-descriptions-item>
                          </el-descriptions>
                        </div>
                    </el-descriptions-item>
                  </el-descriptions>

                  <el-descriptions v-if="detailsState[props.row.id].data.inspection" title="共用验收信息" :column="4" border class="section-divider">
                    <el-descriptions-item label="验收单号" :span="4">{{ detailsState[props.row.id].data.inspection.inspection_number || '未填写' }}</el-descriptions-item>
                    <el-descriptions-item label="验收照片" :span="4">
                      <el-image v-if="detailsState[props.row.id].data.inspection.inspection_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.inspection.inspection_photo)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.inspection.inspection_photo)]" fit="cover" preview-teleported />
                      <span v-else>未上传</span>
                    </el-descriptions-item>
                  </el-descriptions>

                  <el-descriptions v-if="detailsState[props.row.id].data.reimbursement_details" title="共用报销信息" :column="4" border class="section-divider">
                    <el-descriptions-item label="报销单号">{{ detailsState[props.row.id].data.reimbursement_details.reimbursement_number || '未填写' }}</el-descriptions-item>
                    <el-descriptions-item label="实际报销金额">
                      {{ formatActualAmount(detailsState[props.row.id].data.reimbursement_details.actual_amount) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="报销单照片" :span="4">
                      <el-image
                        v-if="detailsState[props.row.id].data.reimbursement_details.reimbursement_photo"
                        lazy
                        style="width: 50px; height: 50px"
                        :src="resolveMediaUrl(detailsState[props.row.id].data.reimbursement_details.reimbursement_photo)"
                        :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.reimbursement_details.reimbursement_photo)]"
                        fit="cover"
                        preview-teleported
                      />
                      <span v-else>未上传</span>
                    </el-descriptions-item>
                  </el-descriptions>

                  <div class="child-tabs-container section-divider">
                    <h3 class="child-details-title">原始子申请详情</h3>
                    <el-tabs v-model="activeChildTab[props.row.id]" type="border-card">
                      <el-tab-pane v-for="child in detailsState[props.row.id].data.merged_children" :key="child.id" :name="child.id" :label="`子申请: ${child.order_number}`">

                        <el-descriptions title="1. 申请与收货信息" :column="4" border size="small">
                          <el-descriptions-item label="申请人">{{ child.applicant.name }}</el-descriptions-item>
                          <el-descriptions-item label="申请导师">{{ child.applicant_tutor?.name || '无' }}</el-descriptions-item>
                          <el-descriptions-item label="单号" :span="2">{{ child.order_number }}</el-descriptions-item>
                          <el-descriptions-item v-if="child.acceptance" label="收货情况" :span="2">{{ child.acceptance.receiving_status || '未填写' }}</el-descriptions-item>
                          <el-descriptions-item v-if="child.acceptance" label="收货照片" :span="2">
                            <el-image v-if="child.acceptance.acceptance_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.acceptance.acceptance_photo)" :preview-src-list="[resolveMediaUrl(child.acceptance.acceptance_photo)]" fit="cover" preview-teleported />
                            <span v-else>未上传</span>
                          </el-descriptions-item>
                        </el-descriptions>

                        <el-descriptions v-if="child.payment" title="2. 支付信息" :column="4" border class="section-divider" size="small">
                          <el-descriptions-item label="支付截图" :span="4">
                            <el-image v-if="child.payment.payment_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.payment.payment_photo)" :preview-src-list="[resolveMediaUrl(child.payment.payment_photo)]" fit="cover" preview-teleported />
                            <span v-else>未上传</span>
                          </el-descriptions-item>
                        </el-descriptions>

                        <el-descriptions v-if="child.purchase_order" title="3. 请购单" :column="4" border class="section-divider" size="small">
                          <el-descriptions-item label="请购单文件" :span="4">
                            <el-image v-if="child.purchase_order.order_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.purchase_order.order_file)" :preview-src-list="[resolveMediaUrl(child.purchase_order.order_file)]" fit="cover" preview-teleported />
                            <span v-else>未上传</span>
                          </el-descriptions-item>
                        </el-descriptions>

                        <el-descriptions v-if="child.contract" title="4. 合同" :column="4" border class="section-divider" size="small">
                          <el-descriptions-item label="合同文件" :span="4">
                            <el-image v-if="child.contract.contract_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.contract.contract_file)" :preview-src-list="[resolveMediaUrl(child.contract.contract_file)]" fit="cover" preview-teleported />
                            <span v-else>未上传</span>
                          </el-descriptions-item>
                        </el-descriptions>

                        <template v-if="getInvoiceList(child).length">
                          <el-descriptions
                            v-for="(invoice, invoiceIndex) in getInvoiceList(child)"
                            :key="invoice.id || invoiceIndex"
                            :title="`5. 发票信息${getInvoiceList(child).length > 1 ? ' ' + (invoiceIndex + 1) : ''}`"
                            :column="4"
                            border
                            class="section-divider"
                            size="small"
                          >
                            <el-descriptions-item label="发票单号">{{ invoice.invoice_number }}</el-descriptions-item>
                            <el-descriptions-item label="开票公司" :span="3">{{ invoice.company_name || invoice.company }}</el-descriptions-item>
                            <el-descriptions-item label="发票文件" :span="4">
                              <template v-if="invoice.invoice_image">
                                <el-link v-if="isPdfUrl(invoice.invoice_image)" :href="resolveMediaUrl(invoice.invoice_image)" type="primary" target="_blank">查看PDF发票</el-link>
                                <el-image v-else lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(invoice.invoice_image)" :preview-src-list="[resolveMediaUrl(invoice.invoice_image)]" fit="cover" preview-teleported />
                              </template>
                              <span v-else>未上传</span>
                            </el-descriptions-item>
                          </el-descriptions>
                        </template>

                        <el-descriptions v-if="child.reimbursement_details" title="6. 报销信息" :column="4" border class="section-divider" size="small">
                          <el-descriptions-item label="报销单号">{{ child.reimbursement_details.reimbursement_number || '未填写' }}</el-descriptions-item>
                          <el-descriptions-item label="实际报销金额">
                            {{ formatActualAmount(child.reimbursement_details.actual_amount) }}
                          </el-descriptions-item>
                          <el-descriptions-item label="报销单照片" :span="4">
                            <el-image v-if="child.reimbursement_details.reimbursement_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.reimbursement_details.reimbursement_photo)" :preview-src-list="[resolveMediaUrl(child.reimbursement_details.reimbursement_photo)]" fit="cover" preview-teleported />
                            <span v-else>未上传</span>
                          </el-descriptions-item>
                        </el-descriptions>

                      </el-tab-pane>
                    </el-tabs>
                  </div>
                </div>
              </template>
              
              <template v-else>
                  <el-descriptions title="1. 申请与收货信息" :column="4" border>
                      <el-descriptions-item label="申请人">{{ detailsState[props.row.id].data.applicant.name }}</el-descriptions-item>
                      <el-descriptions-item label="申请导师">{{ detailsState[props.row.id].data.applicant.assigned_tutor?.name || '无' }}</el-descriptions-item>
                      <el-descriptions-item v-if="detailsState[props.row.id].data.approved_by" label="审批人">{{ detailsState[props.row.id].data.approved_by.name }}</el-descriptions-item>
                      <el-descriptions-item label="申请日期">{{ new Date(detailsState[props.row.id].data.request_date).toLocaleDateString() }}</el-descriptions-item>
                      <el-descriptions-item label="采购平台">{{ detailsState[props.row.id].data.platform }}</el-descriptions-item>
                      <el-descriptions-item label="单号">{{ detailsState[props.row.id].data.order_number }}</el-descriptions-item>
                      <el-descriptions-item label="总金额" :span="2">¥{{ detailsState[props.row.id].data.total_price }}</el-descriptions-item>
                      <el-descriptions-item v-if="detailsState[props.row.id].data.acceptance" label="收货情况" :span="2">{{ detailsState[props.row.id].data.acceptance.receiving_status || '未填写' }}</el-descriptions-item>
                  <el-descriptions-item v-if="detailsState[props.row.id].data.acceptance" label="收货照片" :span="2">
                      <el-image v-if="detailsState[props.row.id].data.acceptance.acceptance_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.acceptance.acceptance_photo)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.acceptance.acceptance_photo)]" fit="cover" preview-teleported />
                      <span v-else>未上传</span>
                  </el-descriptions-item>
                      <el-descriptions-item label="采购物品" :span="4">
                          <div v-for="(item, index) in detailsState[props.row.id].data.items" :key="item.id" class="item-block-nested">
                              <p class="item-title"><strong>物品 {{ index + 1 }}: {{ item.content }}</strong></p>
                              <el-descriptions :column="3" border size="small">
                                  <el-descriptions-item label="采购类型">{{ item.purchase_type || 'N/A' }}</el-descriptions-item>
                                  <el-descriptions-item label="厂商">{{ item.manufacturer || 'N/A' }}</el-descriptions-item>
                                  <el-descriptions-item label="CAS号">{{ item.cas_number || 'N/A' }}</el-descriptions-item>
                                  <el-descriptions-item label="货号">{{ item.product_number || 'N/A' }}</el-descriptions-item>
                                  <el-descriptions-item label="参数">{{ item.parameters || 'N/A' }}</el-descriptions-item>
                                  <el-descriptions-item label="规格">{{ item.specifications || 'N/A' }}</el-descriptions-item>
                                  <el-descriptions-item label="数量">{{ item.quantity }}</el-descriptions-item>
                                  <el-descriptions-item label="单价">¥{{ item.unit_price }}</el-descriptions-item>
                                  <el-descriptions-item label="采购链接">
                                      <el-link :href="item.purchase_link" type="primary" target="_blank" v-if="item.purchase_link">点击跳转</el-link>
                                      <span v-else>N/A</span>
                                  </el-descriptions-item>
                              </el-descriptions>
                          </div>
                      </el-descriptions-item>
                  </el-descriptions>

                  <el-descriptions v-if="detailsState[props.row.id].data.payment" title="2. 支付信息" :column="4" border class="section-divider">
                      <el-descriptions-item label="支付截图" :span="4">
                          <el-image v-if="detailsState[props.row.id].data.payment.payment_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.payment.payment_photo)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.payment.payment_photo)]" fit="cover" preview-teleported />
                          <span v-else>未上传</span>
                      </el-descriptions-item>
                  </el-descriptions>

                  <el-descriptions v-if="detailsState[props.row.id].data.purchase_order" title="3. 请购单" :column="4" border class="section-divider">
                      <el-descriptions-item label="请购单文件" :span="4">
                          <el-image v-if="detailsState[props.row.id].data.purchase_order.order_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.purchase_order.order_file)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.purchase_order.order_file)]" fit="cover" preview-teleported />
                          <span v-else>未上传</span>
                      </el-descriptions-item>
                  </el-descriptions>

                  <el-descriptions v-if="detailsState[props.row.id].data.contract" title="4. 合同" :column="4" border class="section-divider">
                      <el-descriptions-item label="合同文件" :span="4">
                          <el-image v-if="detailsState[props.row.id].data.contract.contract_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.contract.contract_file)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.contract.contract_file)]" fit="cover" preview-teleported />
                          <span v-else>未上传</span>
                      </el-descriptions-item>
                  </el-descriptions>

                  <template v-if="getInvoiceList(detailsState[props.row.id].data).length">
                    <el-descriptions
                      v-for="(invoice, invoiceIndex) in getInvoiceList(detailsState[props.row.id].data)"
                      :key="invoice.id || invoiceIndex"
                      :title="`5. 发票信息${getInvoiceList(detailsState[props.row.id].data).length > 1 ? ' ' + (invoiceIndex + 1) : ''}`"
                      :column="4"
                      border
                      class="section-divider"
                    >
                      <el-descriptions-item label="发票单号">{{ invoice.invoice_number }}</el-descriptions-item>
                      <el-descriptions-item label="开票公司" :span="3">{{ invoice.company_name || invoice.company }}</el-descriptions-item>
                      <el-descriptions-item label="发票文件" :span="4">
                        <template v-if="invoice.invoice_image">
                          <el-link v-if="isPdfUrl(invoice.invoice_image)" :href="resolveMediaUrl(invoice.invoice_image)" type="primary" target="_blank">查看PDF发票</el-link>
                          <el-image v-else lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(invoice.invoice_image)" :preview-src-list="[resolveMediaUrl(invoice.invoice_image)]" fit="cover" preview-teleported />
                        </template>
                        <span v-else>未上传</span>
                      </el-descriptions-item>
                    </el-descriptions>
                  </template>

                  <el-descriptions v-if="detailsState[props.row.id].data.inspection" title="6. 验收信息" :column="4" border class="section-divider">
                      <el-descriptions-item label="验收单号" :span="4">{{ detailsState[props.row.id].data.inspection.inspection_number || '未填写' }}</el-descriptions-item>
                      <el-descriptions-item label="验收照片" :span="4">
                          <el-image v-if="detailsState[props.row.id].data.inspection.inspection_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.inspection.inspection_photo)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.inspection.inspection_photo)]" fit="cover" preview-teleported />
                          <span v-else>未上传</span>
                      </el-descriptions-item>
                  </el-descriptions>

                  <el-descriptions v-if="detailsState[props.row.id].data.reimbursement_details" title="7. 报销信息" :column="4" border class="section-divider">
                      <el-descriptions-item label="报销单号">{{ detailsState[props.row.id].data.reimbursement_details.reimbursement_number || '未填写' }}</el-descriptions-item>
                      <el-descriptions-item label="实际报销金额">
                        {{ formatActualAmount(detailsState[props.row.id].data.reimbursement_details.actual_amount) }}
                      </el-descriptions-item>
                      <el-descriptions-item label="报销单照片" :span="4">
                          <el-image v-if="detailsState[props.row.id].data.reimbursement_details.reimbursement_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.reimbursement_details.reimbursement_photo)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.reimbursement_details.reimbursement_photo)]" fit="cover" preview-teleported />
                          <span v-else>未上传</span>
                      </el-descriptions-item>
                  </el-descriptions>

              </template>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="单号" width="140">
        <template #default="scope">
          <span :class="scope.row.isMergedGroup ? 'multi-order' : 'nowrap'">{{ scope.row.order_number || 'N/A' }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="invoiceLabel" min-width="180">
        <template #default="scope">
          <template v-if="scope.row.isMergedGroup">
            <span class="nowrap"></span>
          </template>
          <template v-else>
            <el-tooltip v-if="getInvoiceDisplay(scope.row).tooltip" :content="getInvoiceDisplay(scope.row).tooltip" placement="top">
              <span class="nowrap">{{ getInvoiceDisplay(scope.row).text }}</span>
            </el-tooltip>
            <span v-else class="nowrap">{{ getInvoiceDisplay(scope.row).text }}</span>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="总金额" width="110">
        <template #default="scope">¥{{ scope.row.total_price }}</template>
      </el-table-column>
      <el-table-column v-if="isPrintMode" label="报销实际金额" width="130">
        <template #default="scope">
          <span v-if="getActualAmountDisplay(scope.row) !== null">¥{{ getActualAmountDisplay(scope.row) }}</span>
          <span v-else>未填写</span>
        </template>
      </el-table-column>
      <el-table-column label="采购人员" width="120">
        <template #default="scope">
          {{ getHandlerName(scope.row) }}
        </template>
      </el-table-column>
      <el-table-column prop="applicant.name" label="申请人" width="120" />
      <el-table-column prop="request_date" label="申请日期" width="120" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="scope">
          <template v-if="isPrintMode">
            <el-button
              type="primary"
              size="small"
              @click="handlePackagePrint(scope.row)"
              :loading="isPackaging && currentPackagingId === scope.row.id"
            >
              打包当前报销信息
            </el-button>
          </template>
          <template v-else>
            <template v-if="scope.row.isMergedGroup">
              <el-button type="warning" size="small" @click="cancelMergedGroup">取消合并</el-button>
              <el-button type="success" size="small" @click="openUploadDialog(scope.row)" style="margin-left: 10px;">上传报销</el-button>
            </template>
            <template v-else-if="isPersistedMerged(scope.row)">
              <el-button
                type="warning"
                size="small"
                @click="handleUnmerge(scope.row)"
                :loading="isUnmerging && currentUnmergeId === scope.row.id"
              >
                取消合并
              </el-button>
              <el-button type="success" size="small" @click="openUploadDialog(scope.row)" style="margin-left: 10px;">上传报销</el-button>
            </template>
            <template v-else>
              <el-button type="primary" size="small" @click="openEditDialog(scope.row)">编辑</el-button>
              <el-button type="success" size="small" @click="openUploadDialog(scope.row)" style="margin-left: 10px;">上传报销</el-button>
            </template>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <div class="footer-actions" v-if="!isPrintMode">
      <el-button type="success" @click="handlePackage" :disabled="selectedRequests.length === 0" :loading="isPackaging">
        <el-icon style="margin-right: 5px;"><Box /></el-icon>
        一键打包选中项附件
      </el-button>
    </div>
    <el-pagination
      v-if="!showSelectedOnly && total > 0"
      class="pagination"
      background
      layout="total, sizes, prev, pager, next, jumper"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      @current-change="handlePageChange"
      @size-change="handlePageSizeChange"
    />
    <PublicEditReimbursementDialog v-model="publicDialogVisible" :request="editingRequest" @save-success="handleSaveSuccess" />
    
    <C2cEditReimbursementDialog v-model="c2cDialogVisible" :request="editingRequest" @save-success="handleSaveSuccess" />
    <ReimbursementDialog v-model="reimbursementDialogVisible" :request-id="reimbursementRequestIds" @upload-success="handleUploadSuccess" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed, nextTick } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search, Box } from '@element-plus/icons-vue';
import PublicEditReimbursementDialog from '@/components/PublicEditReimbursementDialog.vue';
import C2cEditReimbursementDialog from '@/components/C2cEditReimbursementDialog.vue';
import ReimbursementDialog from '@/components/ReimbursementDialog.vue'; // 【新增】导入新弹窗

const props = defineProps({
  requests: { type: Array, required: true },
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  initialFilters: { type: Object, default: () => ({}) },
  showInvoiceFilter: { type: Boolean, default: true },
  mode: { type: String, default: 'reimbursement' },
});
const emit = defineEmits(['refresh-data', 'filter-change', 'page-change', 'page-size-change']);

const tableRef = ref(null);
const selectedRequests = ref([]);
const selectedMap = reactive({});
const showSelectedOnly = ref(false);
const isSyncingSelection = ref(false);
const mergedGroup = ref(null);
const MERGED_GROUP_STORAGE_KEY = 'pendingReimbursementMergedGroup';
const reimbursementRequestIds = ref(null);
const isPackaging = ref(false);
const currentPackagingId = ref(null);
const isUnmerging = ref(false);
const currentUnmergeId = ref(null);
const editingRequest = ref(null);
const publicDialogVisible = ref(false);
const c2cDialogVisible = ref(false);
const reimbursementDialogVisible = ref(false); // 【新增】新弹窗的状态
const applicantOptions = ref([]);
const procurementStaffOptions = ref([]);
const filters = reactive({
  dateRange: null,
  applicant: null,
  handler: null,
  amountSort: null,
  invoiceNumber: '',
  searchQuery: '',
});
const defaultFilters = {
  dateRange: null,
  applicant: null,
  handler: null,
  amountSort: null,
  invoiceNumber: '',
  searchQuery: '',
};

const isPrintMode = computed(() => props.mode === 'print');

const detailsState = reactive({});
const activeChildTab = reactive({});
const mediaVersion = ref(Date.now());
const bumpMediaVersion = () => {
  mediaVersion.value = Date.now();
};

const extractBlobErrorMessage = async (error, fallbackMessage) => {
  const responseData = error?.response?.data;
  if (responseData instanceof Blob) {
    try {
      const text = await responseData.text();
      const parsed = JSON.parse(text);
      if (parsed?.error) return parsed.error;
      if (parsed?.detail) return parsed.detail;
    } catch (parseError) {
      // ignore parse errors and use fallback below
    }
  }
  return error?.response?.data?.error || error?.response?.data?.detail || fallbackMessage;
};

const handleExpandChange = (row, expandedRows) => {
    const isExpanded = expandedRows.some(r => r.id === row.id);
    if (!isExpanded) return;
    if (row?.isMergedGroup) {
        if (!detailsState[row.id]?.data) {
            fetchMergedDetails(row);
        }
        return;
    }
    // 未缓存详情时再拉取
    if (!detailsState[row.id]?.data) {
        fetchDetails(row);
    }
};

const fetchDetails = async (request) => {
    const requestId = request.id;
    if (!detailsState[requestId]) {
        detailsState[requestId] = reactive({ isLoading: false, data: null });
    }
    detailsState[requestId].isLoading = true;
    try {
        const response = await apiClient.get(`/procurement/full-process-requests/${requestId}/`);
        detailsState[requestId].data = response.data;
        if (response.data.merged_children?.length > 0) {
            activeChildTab[requestId] = response.data.merged_children[0].id;
        }
    } catch (error) {
        ElMessage.error('获取合并申请详情失败，请重试。');
        if (tableRef.value) tableRef.value.toggleRowExpansion(request, false);
    } finally {
        detailsState[requestId].isLoading = false;
    }
};

const buildMergedDetailsData = (children, row) => {
  const orderNumbers = children.map(child => child.order_number).filter(Boolean).join('、');
  const totalSum = children.reduce((total, child) => {
    const value = Number(child.total_price || 0);
    return total + (Number.isNaN(value) ? 0 : value);
  }, 0);
  const applicantNames = Array.from(new Set(children.map(child => child.applicant?.name).filter(Boolean)));
  const mergedItems = [];
  children.forEach((child) => {
    (child.items || []).forEach((item) => {
      mergedItems.push({
        ...item,
        original_applicant_name: item.original_applicant_name || child.applicant?.name || item.original_applicant_name
      });
    });
  });
  return {
    id: row.id,
    order_number: orderNumbers,
    total_price: totalSum.toFixed(2),
    applicant: { name: applicantNames.length ? `${applicantNames.join(', ')} (合并)` : '' },
    items: mergedItems,
    merged_children: children,
  };
};

const fetchMergedDetails = async (row) => {
  const requestId = row.id;
  if (!detailsState[requestId]) {
    detailsState[requestId] = reactive({ isLoading: false, data: null });
  }
  detailsState[requestId].isLoading = true;
  try {
    const ids = Array.isArray(row.mergedSourceIds) && row.mergedSourceIds.length > 0
      ? row.mergedSourceIds
      : (mergedGroup.value?.items || []).map(item => item.id);
    if (!ids.length) {
      detailsState[requestId].data = null;
      return;
    }
    const responses = await Promise.all(
      ids.map(id => apiClient.get(`/procurement/full-process-requests/${id}/`))
    );
    const children = responses.map(res => res.data);
    detailsState[requestId].data = buildMergedDetailsData(children, row);
    if (children.length > 0) {
      activeChildTab[requestId] = children[0].id;
    }
  } catch (error) {
    ElMessage.error('获取合并申请详情失败，请重试。');
    if (tableRef.value) tableRef.value.toggleRowExpansion(row, false);
  } finally {
    detailsState[requestId].isLoading = false;
  }
};


const buildMergedRow = (items) => {
  const orderNumbers = items.map(item => item.order_number).filter(Boolean).join('、');
  const totalSum = items.reduce((total, item) => {
    const value = Number(item.total_price || 0);
    return total + (Number.isNaN(value) ? 0 : value);
  }, 0).toFixed(2);
  const handler = items[0]?.handler || null;
  const handlerName = items[0]?.handler_name || null;
  return {
    id: `merged_${Date.now()}`,
    isMergedGroup: true,
    mergedSourceIds: items.map(item => item.id),
    order_number: orderNumbers,
    invoice: null,
    invoices: [],
    total_price: totalSum,
    handler,
    handler_name: handlerName,
    applicant: { name: '' },
    request_date: '',
  };
};

const persistMergedGroup = () => {
  try {
    localStorage.removeItem(MERGED_GROUP_STORAGE_KEY);
  } catch (error) {
    // ignore
  }
};

const restoreMergedGroup = () => {
  try {
    localStorage.removeItem(MERGED_GROUP_STORAGE_KEY);
  } catch (error) {
    // ignore
  }
  mergedGroup.value = null;
};


const displayedRequests = computed(() => {
  if (showSelectedOnly.value) {
    if (mergedGroup.value) {
      return [mergedGroup.value.row];
    }
    return selectedRequests.value;
  }
  if (!mergedGroup.value) {
    return props.requests;
  }
  const mergedIds = new Set(mergedGroup.value.items.map(item => item.id));
  const filtered = props.requests.filter(item => !mergedIds.has(item.id));
  return [mergedGroup.value.row, ...filtered];
});

const updateSelectedRequests = () => {
  selectedRequests.value = Object.values(selectedMap);
};

const handleSelectionChange = (selection) => {
  if (isSyncingSelection.value) return;
  const currentIds = new Set(displayedRequests.value.map(item => item.id));
  const selectedIds = new Set(selection.map(item => item.id));

  currentIds.forEach((id) => {
    if (!selectedIds.has(id)) {
      delete selectedMap[id];
    }
  });
  selection.forEach((item) => {
    selectedMap[item.id] = item;
  });
  updateSelectedRequests();
};

const selectedTotal = computed(() => {
  const sum = selectedRequests.value.reduce((total, item) => {
    const value = Number(item.total_price || 0);
    return total + (Number.isNaN(value) ? 0 : value);
  }, 0);
  return sum.toFixed(2);
});

const clearSelectionState = async () => {
  Object.keys(selectedMap).forEach((key) => {
    delete selectedMap[key];
  });
  selectedRequests.value = [];
  showSelectedOnly.value = false;
  if (tableRef.value) {
    await nextTick();
    tableRef.value.clearSelection();
  }
};

const syncTableSelection = async () => {
  if (!tableRef.value) return;
  isSyncingSelection.value = true;
  await nextTick();
  tableRef.value.clearSelection();
  displayedRequests.value.forEach((row) => {
    if (selectedMap[row.id]) {
      tableRef.value.toggleRowSelection(row, true);
    }
  });
  isSyncingSelection.value = false;
};

const isRowSelectable = (row) => {
  return !row.isMergedGroup;
};

const isPersistedMerged = (row) => {
  return Array.isArray(row?.merged_children) && row.merged_children.length > 0;
};

const openEditDialog = (request) => {
  editingRequest.value = request;
  if (request.expense_type === 'public') {
    publicDialogVisible.value = true;
  } else if (request.expense_type === 'c2c') {
    c2cDialogVisible.value = true;
  } else {
    ElMessage.error('未知的申请类型，无法编辑！');
  }
};

// 【新增】"上传报销" 按钮的处理器
const openUploadDialog = (request) => {
  editingRequest.value = request;
  if (request?.isMergedGroup && Array.isArray(request.mergedSourceIds)) {
    reimbursementRequestIds.value = request.mergedSourceIds;
  } else if (Array.isArray(request?.merged_children) && request.merged_children.length > 0) {
    reimbursementRequestIds.value = request.merged_children.map(child => child.id);
  } else {
    reimbursementRequestIds.value = request?.id || null;
  }
  reimbursementDialogVisible.value = true;
};

const handleSaveSuccess = (updatedRequest = null) => {
  bumpMediaVersion();
  publicDialogVisible.value = false;
  c2cDialogVisible.value = false;
  const target = updatedRequest || editingRequest.value;
  if (target?.id) {
    const reqId = target.id;
    if (!detailsState[reqId]) {
      detailsState[reqId] = reactive({ isLoading: false, data: null });
    }
    if (updatedRequest) {
      detailsState[reqId].data = updatedRequest;
      detailsState[reqId].isLoading = false;
      editingRequest.value = updatedRequest;
    } else {
      detailsState[reqId].data = null;
      fetchDetails({ id: reqId });
    }
  }
  emit('refresh-data');
};

// 【新增】"上传报销" 弹窗成功的回调
const handleUploadSuccess = () => {
  bumpMediaVersion();
  reimbursementDialogVisible.value = false;
  // 刷新数据，使条目移出“待报销”列表
  emit('refresh-data'); 
  
  // 同样清理详情缓存
  if (editingRequest.value) {
    const reqId = editingRequest.value.id;
    if (detailsState[reqId]) {
      detailsState[reqId].data = null; 
    }
  }
};

const handlePackage = async () => {
  isPackaging.value = true;
  try {
    const request_ids = selectedRequests.value.map(req => req.id);
    const response = await apiClient.post('/procurement/package-receipts/', { request_ids }, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `采购报销附件_${new Date().toISOString().slice(0, 10)}.zip`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    if (selectedRequests.value.length >= 2) {
      try {
        await apiClient.post('/procurement/merge-requests/', { request_ids });
        ElMessage.success('已同步合并信息，所有审批角色可见。');
        persistMergedGroup();
        emit('refresh-data');
      } catch (mergeError) {
        ElMessage.error(mergeError.response?.data?.error || '合并失败，请重试。');
      }
    }
    await clearSelectionState();
  } catch (error) {
    ElMessage.error(await extractBlobErrorMessage(error, '打包失败！'));
  } finally {
    isPackaging.value = false;
  }
};

const handlePackagePrint = async (row) => {
  if (!row?.id) return;
  isPackaging.value = true;
  currentPackagingId.value = row.id;
  try {
    const response = await apiClient.get(
      `/procurement/requests/${row.id}/package-reimbursement-images/`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    let filename = `${row.order_number || row.id}_报销图片.zip`;
    const disposition = response.headers['content-disposition'];
    if (disposition) {
      const match = disposition.match(/filename=\"(.+?)\"/);
      if (match && match[1]) {
        filename = decodeURIComponent(match[1]);
      }
    }
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    ElMessage.error('打包报销图片失败！');
  } finally {
    isPackaging.value = false;
    currentPackagingId.value = null;
  }
};

const cancelMergedGroup = () => {
  mergedGroup.value = null;
  showSelectedOnly.value = false;
  try {
    localStorage.removeItem(MERGED_GROUP_STORAGE_KEY);
  } catch (error) {
    // ignore
  }
};

const handleUnmerge = (row) => {
  if (!row?.id) return;
  ElMessageBox.confirm(
    '确定要撤销该合并单吗？撤销后将恢复为合并前的子申请状态。',
    '确认撤销合并',
    { confirmButtonText: '确定撤销', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    isUnmerging.value = true;
    currentUnmergeId.value = row.id;
    try {
      await apiClient.post(`/procurement/requests/${row.id}/unmerge/`);
      ElMessage.success('合并已撤销。');
      emit('refresh-data');
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '撤销合并失败，请重试。');
    } finally {
      isUnmerging.value = false;
      currentUnmergeId.value = null;
    }
  }).catch(() => {
    ElMessage.info('已取消撤销操作');
  });
};

const applyFilters = () => {
  emit('filter-change', { ...filters });
};

const resetFilters = () => {
  Object.assign(filters, defaultFilters);
  clearSelectionState();
  applyFilters();
};

const formatActualAmount = (amount) => {
  if (amount === null || amount === undefined || amount === '') {
    return '未填写';
  }
  const value = Number(amount);
  const display = Number.isFinite(value) ? value.toFixed(2) : String(amount);
  return `¥${display}`;
};

const getActualAmountDisplay = (row) => {
  if (row?.reimbursement_details?.actual_amount !== null && row?.reimbursement_details?.actual_amount !== undefined) {
    const value = Number(row.reimbursement_details.actual_amount);
    return Number.isFinite(value) ? value.toFixed(2) : row.reimbursement_details.actual_amount;
  }
  if (Array.isArray(row?.merged_children) && row.merged_children.length > 0) {
    let sum = 0;
    let hasValue = false;
    row.merged_children.forEach((child) => {
      const amount = child?.reimbursement_details?.actual_amount;
      if (amount !== null && amount !== undefined && amount !== '') {
        const value = Number(amount);
        if (Number.isFinite(value)) {
          sum += value;
        }
        hasValue = true;
      }
    });
    return hasValue ? sum.toFixed(2) : null;
  }
  return null;
};

const fetchFilterOptions = async () => {
  try {
    const res = await apiClient.get('/users/');
    applicantOptions.value = res.data;
    procurementStaffOptions.value = res.data.filter(
      user => Array.isArray(user.roles) && user.roles.some(role => role.name === '采购人员')
    );
  } catch (error) {
    ElMessage.error('获取申请人列表失败');
  }
};

const syncFilters = (incomingFilters) => {
  Object.assign(filters, defaultFilters, incomingFilters || {});
};

onMounted(() => {
  syncFilters(props.initialFilters);
  fetchFilterOptions();
  restoreMergedGroup();
});

watch(() => props.initialFilters, (newFilters) => {
  syncFilters(newFilters);
}, { deep: true });

watch(() => props.requests, () => {
  restoreMergedGroup();
}, { deep: true });

watch(displayedRequests, () => {
  syncTableSelection();
});

const handlePageChange = (newPage) => {
  emit('page-change', newPage);
};

const handlePageSizeChange = (newSize) => {
  emit('page-size-change', newSize);
};

const resolveMediaUrl = (url) => {
  if (!url) return '';
  const raw = String(url);
  const normalized = raw.split('\\').join('/');
  const mediaIndex = normalized.indexOf('/media/');
  let resolved = '';
  if (mediaIndex !== -1) {
    resolved = normalized.slice(mediaIndex);
  } else if (normalized.includes('media/')) {
    resolved = '/' + normalized.slice(normalized.indexOf('media/'));
  } else if (normalized.startsWith('/')) {
    resolved = normalized;
  } else if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
    resolved = normalized;
  } else {
    resolved = `/media/${normalized.replace(/^\/+/, '')}`;
  }
  if (!resolved) return '';
  const separator = resolved.includes('?') ? '&' : '?';
  return `${resolved}${separator}v=${mediaVersion.value}`;
};

const getFileExtension = (url = '') => {
  const cleanUrl = String(url).split('?')[0].split('#')[0];
  const index = cleanUrl.lastIndexOf('.');
  return index === -1 ? '' : cleanUrl.slice(index + 1).toLowerCase();
};

const isPdfUrl = (url) => getFileExtension(url) === 'pdf';

const sortInvoices = (list) => {
  if (!Array.isArray(list)) return [];
  return [...list].sort((a, b) => {
    const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
    const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
    if (Number.isNaN(aTime) && Number.isNaN(bTime)) return 0;
    if (Number.isNaN(aTime)) return 1;
    if (Number.isNaN(bTime)) return -1;
    return bTime - aTime;
  });
};

const getInvoiceList = (row) => {
  const list = row?.invoices;
  const normalized = Array.isArray(list) && list.length > 0
    ? list
    : (row?.invoice ? [row.invoice] : []);
  return sortInvoices(normalized);
};

const getInvoiceDisplay = (row) => {
  const numbers = getInvoiceList(row).map(item => item.invoice_number).filter(Boolean);
  if (numbers.length === 0) return { text: '\u672a\u586b\u5199', tooltip: '' };
  if (numbers.length === 1) return { text: numbers[0], tooltip: '' };
  return { text: `${numbers[0]} \u7b49${numbers.length}\u5f20`, tooltip: numbers.join('\u3001') };
};

const invoiceLabel = '\u53d1\u7968\u5355\u53f7';

const getHandlerName = (row) => {
  if (row?.handler?.name) return row.handler.name;
  if (row?.handler_name) return row.handler_name;
  if (row?.handler) {
    const matched = procurementStaffOptions.value.find(user => user.id === row.handler)
      || applicantOptions.value.find(user => user.id === row.handler);
    return matched ? matched.name : String(row.handler);
  }
  return '未指定';
};
</script>

<style scoped>
.controls-container { margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 15px; }
.selection-summary { margin-bottom: 12px; font-size: 14px; color: #303133; font-weight: 500; }
.selection-summary :deep(.el-button) { margin-left: 10px; }
.nowrap { white-space: nowrap; }
.multi-order { white-space: normal; word-break: break-all; line-height: 1.4; }
.actions-item { margin-left: auto; }
.actions-item :deep(.el-form-item__content) { display: flex; gap: 10px; }
.footer-actions { margin-top: 20px; padding-top: 20px; border-top: 1px solid #e4e7ed; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
.details-wrapper { min-height: 150px; }
.details-container { padding: 20px; background-color: #fafafa; }
.section-divider { margin-top: 15px; }
.child-tabs-container { margin-top: 20px; }
.item-list { list-style: none; padding: 0; margin: 0; }
.item-list li { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.child-request-section { margin-top: 20px; padding: 16px; border: 1px dashed #dcdfe6; border-radius: 4px; }
.child-section-title { margin: 0 0 16px 0; font-size: 16px; color: #303133; }
.item-block-nested { margin-bottom: 12px; }
.item-block-nested:last-child { margin-bottom: 0; }
.item-title { margin: 0 0 8px 0; font-size: 14px; color: #303133; }
.child-details-title {
  margin-bottom: 16px;
  font-size: 16px;
  color: #303133;
}
</style>
