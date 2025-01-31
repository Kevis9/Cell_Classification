library(batchelor)
library(Seurat)

read_data <- function(path) {
    # return matrix
    data = as.matrix(read.csv(path, row.names=1))
    return (data)
}

read_label <- function(path) {
    #return matrix
    label = as.matrix(read.csv(path))
    return (label)
}

select_feature <- function(data,label,nf=2000){
    M <- nrow(data); new.label <- label[,1]
    pv1 <- sapply(1:M, function(i){
        mydataframe <- data.frame(y=as.numeric(data[i,]), ig=new.label)
        fit <- aov(y ~ ig, data=mydataframe)
        summary(fit)[[1]][["Pr(>F)"]][1]})
    names(pv1) <- rownames(data)
    pv1.sig <- names(pv1)[order(pv1)[1:nf]]
    egen <- unique(pv1.sig)
    return (egen)
}

normalize_data <- function(data) {
#     data <- as.matrix(Seurat:::NormalizeData.default(data,verbose=F))
    data = t(data) # transpose to cell * gene
    row_sum = apply(data, 1, sum)
    mean_t = mean(row_sum)

    row_sum[row_sum==0] = 1
    data = data/row_sum * mean_t
    # gene * cell
    data = t(data)
    return (data)

}



main <- function(ref_data_path, query_data_path, ref_label_path, ref_save_path, query_save_path){

    ref_data = t(read_data(ref_data_path)) # gene x cell
    ref_label = read_label(ref_label_path)
    query_data = t(read_data(query_data_path)) # gene x cell

    # gene selection
    print(dim(ref_data))
    print(dim(ref_label))
    sel.features <- select_feature(ref_data, ref_label)
    sel.ref_data = ref_data[sel.features, ]
    sel.query_data = query_data[sel.features, ]
    
    # Norm
    norm.ref_data = normalize_data(sel.ref_data)
    norm.query_data = normalize_data(sel.query_data)

    # Mnn correct
#     out = mnnCorrect(norm.ref_data, norm.query_data, cos.norm.in = FALSE, cos.norm.out=FALSE)
#     out = mnnCorrect(norm.ref_data, norm.query_data)

#     out = mnnCorrect(norm.ref_data, norm.query_data, sigma=0.3)

#     new_data = out@assays@data@listData$corrected

#     new.ref_data = t(out@assays@data$corrected[,out$batch==1])
#     new.query_data = t(out@assays@data$corrected[,out$batch==2])

    new.ref_data = t(norm.ref_data)
    new.query_data = t(norm.query_data)

#     write.csv(new.ref_data, file=paste(save_path, 'ref', 'data_1.csv', sep='/'), row.names=TRUE)
#     write.csv(new.query_data, file=paste(save_path, 'query', 'data_1.csv', sep='/'), row.names=TRUE)
    write.csv(new.ref_data, file=ref_save_path, row.names=TRUE)
    write.csv(new.query_data, file=query_save_path, row.names=TRUE)

}


args = commandArgs(trailingOnly = TRUE)
base_path = args[[1]]
ref_data_path = paste(base_path, 'raw_data' ,'ref', 'data_1.csv', sep='/')
query_data_path = paste(base_path, 'raw_data', 'query', 'data_1.csv', sep='/')
ref_label_path = paste(base_path, 'raw_data', 'ref', 'label_1.csv', sep='/')

ref_save_path = paste(base_path, 'data', 'ref', 'data_1.csv',sep='/')
query_save_path = paste(base_path, 'data', 'query', 'data_1.csv', sep='/')

print("Path is")
print(base_path)
main(ref_data_path, query_data_path, ref_label_path, ref_save_path, query_save_path)






# base_path = 'E:/YuAnHuang/kevislin/Cell_Classification/experiment/multi_ref/Haber/'
# args = commandArgs(trailingOnly = TRUE)
# base_path = args[[1]]
# print(base_path)
# # multi ref
# for(i in 2:3) {
#     query_data_name = paste('data_', i, '.csv', sep='')
#     ref_data_path = paste(base_path, 'raw_data' ,'ref', 'data_1.csv', sep='/')
#     query_data_path = paste(base_path, 'raw_data', 'ref', query_data_name, sep='/')
#     ref_label_path = paste(base_path, 'raw_data', 'ref', 'label_1.csv', sep='/')
#
#     ref_save_path = paste(base_path, 'data', 'ref', 'data_1.csv',sep='/')
#     query_save_path = paste(base_path, 'data', 'ref', query_data_name, sep='/')
#
#     print("Path is")
#     print(base_path)
#
#     main(ref_data_path, query_data_path, ref_label_path, ref_save_path, query_save_path)
# }
#
# # query
# # base_path = args[[1]]
#
# query_data_name = paste('data_', 1, '.csv', sep='')
# ref_data_path = paste(base_path, 'raw_data' ,'ref', 'data_1.csv', sep='/')
# query_data_path = paste(base_path, 'raw_data', 'query', query_data_name, sep='/')
# ref_label_path = paste(base_path, 'raw_data', 'ref', 'label_1.csv', sep='/')
#
# ref_save_path = paste(base_path, 'data', 'ref', 'data_1.csv',sep='/')
# query_save_path = paste(base_path, 'data', 'query', query_data_name, sep='/')
# main(ref_data_path, query_data_path, ref_label_path, ref_save_path, query_save_path)

# 